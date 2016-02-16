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



class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    
    officialBotPublicKey = None
    officialBotPublicKeyFileName = None
    officialBotPublicKeyFileTime = None
    
    
    @staticmethod
    def staticInit():
        pgp = email_sec_cache.Pgp()
        HTTPRequestHandler.officialBotPublicKey = pgp.getOfficialPublicKey()
        HTTPRequestHandler.officialBotPublicKeyFileTime = os.stat(email_sec_cache.Pgp.officialBotKeysFilePath).st_mtime
        HTTPRequestHandler.officialBotPublicKeyFileName = email_sec_cache.Pgp.botEmailAddress + " pub.asc"
    
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
            
        content = self.applyParameters(content)
            
        contentAsBytes = bytes(content, "utf-8")
        self.send_header("Content-Length", len(contentAsBytes))
        self.send_header("Last-Modified", self.date_time_string(modTime))
        self.end_headers()
        
        return io.BytesIO(contentAsBytes)
    
    def getGetResponse(self):
        if self.getPathComponents() == [HTTPRequestHandler.officialBotPublicKeyFileName]:
            return \
                HTTPRequestHandler.officialBotPublicKey, \
                HTTPRequestHandler.officialBotPublicKeyFileName, \
                HTTPRequestHandler.officialBotPublicKeyFileTime

        fsPath = self.getFSPath()
        if fsPath is None:
            return None, None, None
        try:
            with open(fsPath, "r", encoding="utf-8") as f:
                content = f.read()
                statInfo = os.stat(f.fileno())
                modTime = statInfo.st_mtime
            return content, fsPath, modTime
        except OSError:
            return None, None, None
    
    def getRootFSPath(self):
        return os.path.join(email_sec_cache.resourceDir, "html")
    
    def getPathComponents(self):
        path = self.path
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        try:
            path = urllib.parse.unquote(path, errors="surrogatepass")
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        
        pathComponents = path.split("/")
        if ".." in pathComponents:
            return None
        pathComponents = list(filter(None, pathComponents))
        return pathComponents
    
    def getFSPath(self):
        pathComponents = self.getPathComponents()
        if pathComponents is None:
            return None
        
        rootFSPath = self.getRootFSPath()
        fsPath = os.path.join(rootFSPath, *pathComponents)
        if not email_sec_cache.isPathPrefix(fsPath, rootFSPath):
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
        return contentType, contentEncoding
        
        
    def do_POST(self):
        contentType = self.headers["Content-Type"]
        contentTypeValue, contentTypeParameters = cgi.parse_header(contentType)
        if contentTypeValue != "multipart/form-data" or "boundary" not in contentTypeParameters:
            self.send_error(http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        contentTypeParameters["boundary"] = bytes(contentTypeParameters["boundary"], "ascii")
        uploaded = cgi.parse_multipart(self.rfile, contentTypeParameters)
        
        if not ("key" in uploaded and len(uploaded["key"]) > 0):
            self.send_error(http.HTTPStatus.BAD_REQUEST)
        correspondentKey = str(uploaded["key"][0], "ascii")
        emailAddresses = email_sec_cache.Pgp.storeCorrespondentKey(correspondentKey)
        
        self.send_response(http.HTTPStatus.FOUND)
        if emailAddresses != []:
            self.send_header("Location", "key_upload_success.html")
        else:
            self.send_header("Location", "key_upload_error.html")
        self.end_headers()
        

def startKeyUploadServer():
    HTTPRequestHandler.staticInit()
    httpd = socketserver.TCPServer(("", email_sec_cache.keyUploadServerPort), HTTPRequestHandler, bind_and_activate=False)
    httpd.allow_reuse_address = True
    httpd.server_bind()
    httpd.server_activate()
    logging.info("EmailSecCache: Key upload server started")
    threading.Thread(target = httpd.serve_forever).start()
