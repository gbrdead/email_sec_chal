# -*- coding: utf-8 -*-
import http.server
import socketserver
import threading
import email_sec_cache
import os.path
import mimetypes
import shutil
import cgi
import logging
import io
import urllib.parse



class KeyUploadRequestHandler(http.server.BaseHTTPRequestHandler):
    
    initialized = False
    
    rootFSPath = None
    officialBotPublicKeyVirtualFilePaths = []

    officialBotPublicKey = None
    officialBotPublicKeyFileTime = None
    
    
    @staticmethod
    def staticInit():
        if KeyUploadRequestHandler.initialized:
            return
        
        rootFSPath = os.path.join(email_sec_cache.resourceDir, "html")
        rootFSPath = os.path.normpath(rootFSPath)
        KeyUploadRequestHandler.rootFSPath = os.path.normcase(rootFSPath)
        logging.debug("EmailSecCache: key_upload_server: The root file system path is: %s" % KeyUploadRequestHandler.rootFSPath)
        
        pgp = email_sec_cache.Pgp()
        KeyUploadRequestHandler.officialBotPublicKey = pgp.getOfficialPublicKey()
        KeyUploadRequestHandler.officialBotPublicKeyFileTime = os.stat(email_sec_cache.Pgp.officialBotKeysFilePath).st_mtime
        officialBotPublicKeyFileName = email_sec_cache.Pgp.botEmailAddress + " pub.asc"
        logging.debug("EmailSecCache: key_upload_server: The official bot's public key file name is: %s" % officialBotPublicKeyFileName)
        
        KeyUploadRequestHandler.officialBotPublicKeyVirtualFilePaths.append(os.path.join(KeyUploadRequestHandler.rootFSPath, officialBotPublicKeyFileName))
        KeyUploadRequestHandler.officialBotPublicKeyVirtualFilePaths.append(os.path.join(KeyUploadRequestHandler.rootFSPath, officialBotPublicKeyFileName + ".txt"))
        
        logging.debug("EmailSecCache: key_upload_server: Static initialization successful")
        KeyUploadRequestHandler.initialized = True
        
    
    def do_HEAD(self):
        f = self.sendHead()
        if f:
            f.close()
        
    def do_GET(self):
        f = self.sendHead()
        if f:
            try:
                shutil.copyfileobj(f, self.wfile)
            finally:
                f.close()
    
    def sendHead(self):
        
        content, fsPath, modTime = self.getGetResponse()
        if content is None:
            self.send_error(http.HTTPStatus.NOT_FOUND)
            return

        self.send_response(http.HTTPStatus.OK)
        
        contentType, contentEncoding = self.getContentType(fsPath)
        self.send_header("Content-Type", contentType)
        if contentEncoding is not None:
            self.send_header("Content-Encoding", contentEncoding)
            
        if isinstance(content, str):
            content = self.applyParameters(content)
            content = bytes(content, "utf-8")
        
        self.send_header("Content-Length", len(content))
        self.send_header("Last-Modified", self.date_time_string(modTime))
        self.end_headers()
        
        return io.BytesIO(content)
    
    def getGetResponse(self):
        fsPath = self.getFSPath()
        if fsPath is None:
            return None, None, None
        
        if fsPath in KeyUploadRequestHandler.officialBotPublicKeyVirtualFilePaths:
            return \
                KeyUploadRequestHandler.officialBotPublicKey, \
                fsPath, \
                KeyUploadRequestHandler.officialBotPublicKeyFileTime
        
        try:
            with open(fsPath, "r", encoding="utf-8") as f:
                try:
                    content = f.read()
                    statInfo = os.stat(f.fileno())
                except UnicodeDecodeError:
                    with open(fsPath, "rb") as fb:
                        content = fb.read()
                        statInfo = os.stat(fb.fileno())
            return content, fsPath, statInfo.st_mtime
        except OSError:
            logging.debug("EmailSecCache: key_upload_server: Cannot read file: %s" % fsPath, exc_info=True)
            return None, None, None
    
    def getPathComponents(self):
        path = self.path
        logging.debug("EmailSecCache: key_upload_server: Request path: %s" % path)
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        logging.debug("EmailSecCache: key_upload_server: Request path after the removal of query parameters and anchors: %s" % path)
        try:
            path = urllib.parse.unquote(path, errors="surrogatepass")
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        logging.debug("EmailSecCache: key_upload_server: Request path after unquoting: %s" % path)
        
        pathComponents = path.split("/")
        logging.debug("EmailSecCache: key_upload_server: Request path components: %s" % pathComponents)
        pathComponents = list(filter(None, pathComponents))
        logging.debug("EmailSecCache: key_upload_server: Request path components after the removal of empty ones: %s" % pathComponents)
        if ".." in pathComponents:
            logging.warning("EmailSecCache: key_upload_server: Request path traversal attempt")
            return None
        return pathComponents
    
    def getFSPath(self):
        pathComponents = self.getPathComponents()
        if not pathComponents:
            return None
        
        fsPath = os.path.join(KeyUploadRequestHandler.rootFSPath, *pathComponents)
        fsPath = os.path.normpath(fsPath)
        fsPath = os.path.normcase(fsPath)
        logging.debug("EmailSecCache: key_upload_server: Normalized file system path: %s" % fsPath)
        if not email_sec_cache.isPathPrefix(fsPath, KeyUploadRequestHandler.rootFSPath):
            logging.warning("EmailSecCache: key_upload_server: Attempt to access a file outside the root dir")
            return None
        return fsPath
    
    def applyParameters(self, content):
        content = content.replace("@BOT_EMAIL_ADDRESS@", email_sec_cache.Pgp.botEmailAddress)
        return content
    
    def getContentType(self, fsPath):
        if fsPath.lower().endswith(".asc"):
            contentType = "application/pgp-keys"
            contentEncoding = None
        else:
            contentType, contentEncoding = mimetypes.guess_type(fsPath)
            if contentType is None:
                contentType = "application/octet-stream"
                
        logging.debug("EmailSecCache: key_upload_server: Path: %s; Content-Type: %s, Content-Encoding: %s" % (fsPath, contentType, contentEncoding))
        return contentType, contentEncoding
        
        
    def do_POST(self):
        contentType = self.headers["Content-Type"]
        contentTypeValue, contentTypeParameters = cgi.parse_header(contentType)
        if contentTypeValue != "multipart/form-data" or "boundary" not in contentTypeParameters:
            logging.warning("EmailSecCache: key_upload_server: Invalid POST Content-Type: %s" % contentType)
            self.send_error(http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return
        contentTypeParameters["boundary"] = bytes(contentTypeParameters["boundary"], "ascii")
        uploaded = cgi.parse_multipart(self.rfile, contentTypeParameters)
        
        if not ("key" in uploaded and len(uploaded["key"]) > 0):
            self.send_error(http.HTTPStatus.BAD_REQUEST)
            return
        correspondentKey = str(uploaded["key"][0], "ascii")
        emailAddresses = email_sec_cache.Pgp.storeCorrespondentKey(correspondentKey)
        
        self.send_response(http.HTTPStatus.FOUND)
        if emailAddresses != []:
            self.send_header("Location", "key_upload_success.html")
        else:
            self.send_header("Location", "key_upload_error.html")
        self.end_headers()


    def log_message(self, format_, *args):
        realClientAddress = self.headers.get("X-Forwarded-For")
        if realClientAddress is None:
            realClientAddress = self.address_string()
        logging.info("EmailSecCache: key_upload_server: %s - - %s" % (realClientAddress, (format_ % args)))
        

def startKeyUploadServer():
    KeyUploadRequestHandler.staticInit()
    httpd = socketserver.TCPServer(("", email_sec_cache.keyUploadServerPort), KeyUploadRequestHandler, bind_and_activate=False)
    httpd.allow_reuse_address = True
    httpd.server_bind()
    httpd.server_activate()
    logging.info("EmailSecCache: key_upload_server: Successfully started")
    threading.Thread(target = httpd.serve_forever, daemon=True).start()
    return httpd
