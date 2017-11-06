# -*- coding: utf-8 -*-
import http.server
import socketserver
import threading
import email_sec_chal
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
    officialBotKeyFingerprint = None
    officialBotPublicKeyFileTime = None
    
    
    @staticmethod
    def staticInit():
        if KeyUploadRequestHandler.initialized:
            return
        
        KeyUploadRequestHandler.rootFSPath = os.path.join(email_sec_chal.resourceDir, "html")
        KeyUploadRequestHandler.rootFSPath = os.path.normpath(KeyUploadRequestHandler.rootFSPath)
        KeyUploadRequestHandler.rootFSPath = os.path.normcase(KeyUploadRequestHandler.rootFSPath)
        logging.debug("EmailSecChal: key_upload_server: The root file system path is: %s" % KeyUploadRequestHandler.rootFSPath)
        
        with email_sec_chal.Pgp() as pgp:
            KeyUploadRequestHandler.officialBotPublicKey = pgp.getOfficialPublicKey()
            KeyUploadRequestHandler.officialBotPublicKeyFileTime = os.stat(email_sec_chal.Pgp.officialBotKeysFilePath).st_mtime
            officialBotPublicKeyFileName = email_sec_chal.Pgp.botEmailAddress + " pub.asc"
            logging.debug("EmailSecChal: key_upload_server: The official bot's public key file name is: %s" % officialBotPublicKeyFileName)
            KeyUploadRequestHandler.officialBotKeyFingerprint = pgp.officialFingerprints[0]
        
            KeyUploadRequestHandler.officialBotPublicKeyVirtualFilePaths.append(os.path.join(KeyUploadRequestHandler.rootFSPath, officialBotPublicKeyFileName))
            KeyUploadRequestHandler.officialBotPublicKeyVirtualFilePaths.append(os.path.join(KeyUploadRequestHandler.rootFSPath, officialBotPublicKeyFileName + ".txt"))
        
        logging.debug("EmailSecChal: key_upload_server: Static initialization successful")
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
            self.send_error(404)
            return

        self.send_response(200)
        
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
            logging.debug("EmailSecChal: key_upload_server: Cannot read file: %s" % fsPath, exc_info=True)
            return None, None, None
    
    def getPathComponents(self):
        path = self.path
        logging.debug("EmailSecChal: key_upload_server: Request path: %s" % path)
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        logging.debug("EmailSecChal: key_upload_server: Request path after the removal of query parameters and anchors: %s" % path)
        try:
            path = urllib.parse.unquote(path, errors="surrogatepass")
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        logging.debug("EmailSecChal: key_upload_server: Request path after unquoting: %s" % path)
        
        pathComponents = path.split("/")
        logging.debug("EmailSecChal: key_upload_server: Request path components: %s" % pathComponents)
        pathComponents = list(filter(None, pathComponents))
        logging.debug("EmailSecChal: key_upload_server: Request path components after the removal of empty ones: %s" % pathComponents)
        if ".." in pathComponents:
            logging.warning("EmailSecChal: key_upload_server: Request path traversal attempt")
            return None
        return pathComponents
    
    def getFSPath(self):
        pathComponents = self.getPathComponents()
        if pathComponents is None:
            return None
        
        fsPath = os.path.join(KeyUploadRequestHandler.rootFSPath, *pathComponents)
        while os.path.isdir(fsPath):
            fsPath = os.path.join(fsPath, "index.html")
            logging.debug("EmailSecChal: key_upload_server: Added index.html to the file system path: %s" % fsPath)
        fsPath = os.path.normpath(fsPath)
        fsPath = os.path.normcase(fsPath)
        logging.debug("EmailSecChal: key_upload_server: Normalized file system path: %s" % fsPath)
        if not email_sec_chal.isPathPrefix(fsPath, KeyUploadRequestHandler.rootFSPath):
            logging.warning("EmailSecChal: key_upload_server: Attempt to access a file outside the root dir")
            return None
        return fsPath
    
    def applyParameters(self, content):
        content = content.replace("@BOT_EMAIL_ADDRESS@", email_sec_chal.Pgp.botEmailAddress)
        content = content.replace("@BOT_KEY_FINGERPRINT@", KeyUploadRequestHandler.officialBotKeyFingerprint)
        return content
    
    def getContentType(self, fsPath):
        if fsPath.lower().endswith(".asc"):
            contentType = "application/pgp-keys"
            contentEncoding = None
        else:
            contentType, contentEncoding = mimetypes.guess_type(fsPath)
            if contentType is None:
                contentType = "application/octet-stream"
                
        logging.debug("EmailSecChal: key_upload_server: Path: %s; Content-Type: %s, Content-Encoding: %s" % (fsPath, contentType, contentEncoding))
        return contentType, contentEncoding
        
        
    def do_POST(self):
        contentType = self.headers["Content-Type"]
        contentTypeValue, contentTypeParameters = cgi.parse_header(contentType)
        if contentTypeValue != "multipart/form-data" or "boundary" not in contentTypeParameters:
            logging.warning("EmailSecChal: key_upload_server: Invalid POST Content-Type: %s" % contentType)
            self.send_error(415)
            return
        contentTypeParameters["boundary"] = bytes(contentTypeParameters["boundary"], "ascii")
        uploaded = cgi.parse_multipart(self.rfile, contentTypeParameters)
        
        if not ("key" in uploaded and len(uploaded["key"]) > 0):
            self.send_error(400)
            return
        
        try:
            correspondentKey = str(uploaded["key"][0], "ascii")
            emailAddresses = email_sec_chal.Pgp.storeCorrespondentKey(correspondentKey)
        except:
            logging.warning("EmailSecChal: key_upload_server: Cannot import key", exc_info=True)
            emailAddresses = []
        
        self.send_response(302)
        if emailAddresses != []:
            self.send_header("Location", "key_upload_success.html")
        else:
            self.send_header("Location", "key_upload_error.html")
        self.end_headers()


    def log_message(self, format_, *args):
        realClientAddress = self.headers.get("X-Forwarded-For")
        if realClientAddress is None:
            realClientAddress = self.address_string()
        logging.info("EmailSecChal: key_upload_server: %s - - %s" % (realClientAddress, (format_ % args)))
        

def startKeyUploadServer():
    KeyUploadRequestHandler.staticInit()
    httpd = socketserver.TCPServer(("", email_sec_chal.keyUploadServerPort), KeyUploadRequestHandler, bind_and_activate=False)
    httpd.allow_reuse_address = True
    httpd.server_bind()
    httpd.server_activate()
    logging.info("EmailSecChal: key_upload_server: Successfully started")
    threading.Thread(target = httpd.serve_forever, daemon=True).start()
    return httpd
