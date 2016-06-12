# -*- coding: utf-8 -*-
import test.email_sec_cache
import socket
import email_sec_cache
import requests
import shutil
import tempfile
import bs4
import re
import email.utils
import os.path



class KeyUploadServerTests(test.email_sec_cache.Tests):
    
    keyUploadServer = None
    keyUploadUrlPrefix = None

    correspondentEmailAddress = "gbr@voidland.org"
    correspondentKeyId = "9011E1A9"
    correspondentKey = None
    
    stringsRe = re.compile("\S+")
    
    
    @staticmethod
    def findFreePort():
        while True:
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", 0))
                return s.getsockname()[1]
            except:
                pass
            finally:
                if s is not None:
                    try:
                        s.close()
                    except:
                        pass
                    
    @classmethod
    def setUpClass(cls):
        test.email_sec_cache.Tests.setUpClass()

        email_sec_cache.keyUploadServerPort = KeyUploadServerTests.findFreePort()
        email_sec_cache.KeyUploadRequestHandler.initialized = False
        
        KeyUploadServerTests.keyUploadServer = email_sec_cache.startKeyUploadServer()
        KeyUploadServerTests.keyUploadUrlPrefix = "http://localhost:" + str(email_sec_cache.keyUploadServerPort)
        
        KeyUploadServerTests.correspondentKey = test.email_sec_cache.Tests.readPublicKey(KeyUploadServerTests.correspondentEmailAddress, KeyUploadServerTests.correspondentKeyId)

    @classmethod
    def tearDownClass(cls):
        KeyUploadServerTests.keyUploadServer.shutdown()
        KeyUploadServerTests.keyUploadServer.server_close()
        KeyUploadServerTests.keyUploadServer = None
        
        test.email_sec_cache.Tests.tearDownClass()
        
    def setUp(self):
        test.email_sec_cache.Tests.setUp(self)
        db = email_sec_cache.Db()
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM correspondents")

    def tearDown(self):
        test.email_sec_cache.Tests.tearDown(self)
        
        
    def getGetResponse(self, uri, raiseExceptionOnError=True):
        url = KeyUploadServerTests.keyUploadUrlPrefix + uri
        
        headResponse = requests.head(url)
        getResponse = requests.get(url)
        self.assertEqual(headResponse.status_code, getResponse.status_code)
        
        headHeaders = dict(headResponse.headers)
        getHeaders = dict(getResponse.headers)
        del headHeaders["Date"]
        del getHeaders["Date"]
        self.assertEqual(headHeaders, getHeaders)
        
        if raiseExceptionOnError:
            getResponse.raise_for_status()
        return getResponse
            
    def testDefaultUrl(self):
        response = self.getGetResponse("/", raiseExceptionOnError=False)
        self.assertEqual(404, response.status_code)
 
    def testNonExistingFile(self):
        response = self.getGetResponse("/non_existing_file.html", raiseExceptionOnError=False)
        self.assertEqual(404, response.status_code)
 
    def testNonExistingFileInSubdir(self):
        response = self.getGetResponse("/subdir/non_existing_file.html", raiseExceptionOnError=False)
        self.assertEqual(404, response.status_code)
 
    def testBotPublicKeyInSubdir(self):
        response = self.getGetResponse("/subdir/gbr@voidland.voidland.org%20pub.asc", raiseExceptionOnError=False)
        self.assertEqual(404, response.status_code)
        response = self.getGetResponse("/subdir/gbr@voidland.voidland.org%20pub.asc.txt", raiseExceptionOnError=False)
        self.assertEqual(404, response.status_code)
 
    def testNonExistingFileInNonExistingSubdir(self):
        response = self.getGetResponse("/non_existing_subdir/non_existing_file.html", raiseExceptionOnError=False)
        self.assertEqual(404, response.status_code)
 
    def testPathTraversalAttempt(self):
        response = self.getGetResponse("/subdir/../file.html", raiseExceptionOnError=False)
        self.assertEqual(404, response.status_code)
 
 
    def testBotPublicKey(self):
        self.assertBotPublicKey("gbr@voidland.voidland.org%20pub.asc", "application/pgp-keys")
        
    def testBotPublicKeyTxt(self):
        self.assertBotPublicKey("gbr@voidland.voidland.org%20pub.asc.txt", "text/plain")
 
    def assertBotPublicKey(self, officialBotPublicKeyVirtualFilePath, contentType):
        gpg, gnupgHomeDir = email_sec_cache.Pgp.createTempGpg()
        try:
            response = self.getGetResponse("/" + officialBotPublicKeyVirtualFilePath + "?name=value") 
            botPublicKeyFile = tempfile.NamedTemporaryFile(dir = email_sec_cache.tempDir, delete=False, mode="wb")
            try:
                botPublicKeyFile.write(response.content)
                botPublicKeyFile.close()
                 
                keys = gpg.scan_keys(botPublicKeyFile.name)
                self.assertEqual(1, len(keys))
                key = keys[0]
                self.assertEqual("B509A2EB802708CE80C2C3E54897D47A61DC9FE3", key["fingerprint"])
                self.assertEqual("pub", key["type"])
                 
                self.assertEqual(contentType, response.headers["Content-Type"])
                 
            finally:
                email_sec_cache.removeFile(botPublicKeyFile.name)
        finally:
            shutil.rmtree(gnupgHomeDir, ignore_errors=True)
 
    def testExistingFileAndParameterSubstitution(self):
        self.assertExistingFile("/file.html?name=value#anchor", ["word", "gbr@voidland.voidland.org"])
 
    def testExistingFileInSubdir(self):
        self.assertExistingFile("/subdir/fileInSubDir.html#anchor", ["word", "BOT_EMAIL_ADDRESS"])
 
    def assertExistingFile(self, uri, expectedStrings): 
        response = self.getGetResponse(uri)
        self.assertEqual("text/html", response.headers["Content-Type"])
        html = bs4.BeautifulSoup(response.content, "html.parser")
        for el in html.findAll(["script", "style"]):
            el.extract()
        plainText = html.get_text(separator=" ")
        strings = KeyUploadServerTests.stringsRe.findall(plainText)
        self.assertEqual(expectedStrings, strings)            
 
    def testFileTimestamp(self):
        filePath = os.path.join(email_sec_cache.resourceDir, "html", "file.html")
        self.assertLastModified("/file.html", filePath)
         
    def testBotPublicKeyTimestamp(self):
        filePath = os.path.join(email_sec_cache.resourceDir, "officialBot.asc")
        self.assertLastModified("/gbr@voidland.voidland.org%20pub.asc.txt", filePath)
        self.assertLastModified("/gbr@voidland.voidland.org%20pub.asc", filePath)
 
    def assertLastModified(self, uri, filePath):
        response = self.getGetResponse(uri)
        lastModifiedHeader = response.headers["Last-Modified"]
        lastModifiedTime = email.utils.parsedate_to_datetime(lastModifiedHeader).timestamp()
        fileModifiedTime = os.stat(filePath).st_mtime
        self.assertLess(abs(lastModifiedTime - fileModifiedTime), 1)
 
    def testUnknownContentType(self):
        response = self.getGetResponse("/fileWithoutExtension")
        self.assertEqual("application/octet-stream", response.headers["Content-Type"])
        self.assertNotIn("Content-Encoding", response.headers)

    def testGzipContentType(self):
        response = self.getGetResponse("/file.txt.gz") 
        self.assertEqual("text/plain", response.headers["Content-Type"])
        self.assertEqual("gzip", response.headers["Content-Encoding"])
        

    def getPostResponse(self, uri, files=None, data=None):
        url = KeyUploadServerTests.keyUploadUrlPrefix + uri
        return requests.post(url, files=files, data=data, allow_redirects=False)

    def testUploadCorrespondentKey(self):
        files={"key": ("public_key.asc", KeyUploadServerTests.correspondentKey)}
        response = self.getPostResponse("/key_upload", files=files)
        self.assertEqual(302, response.status_code)
        self.assertEqual("key_upload_success.html", response.headers["Location"])
        
        db = email_sec_cache.Db()
        self.assertEqual(KeyUploadServerTests.correspondentKey, db.getCorrespondentKey(KeyUploadServerTests.correspondentEmailAddress))

    def testUploadInvalidContentType(self):
        data={"key": KeyUploadServerTests.correspondentKey}
        response = self.getPostResponse("/key_upload", data=data)
        self.assertEqual(415, response.status_code)
        
        db = email_sec_cache.Db()
        self.assertEqual(None, db.getCorrespondentKey(KeyUploadServerTests.correspondentEmailAddress))

    def testUploadWrongFieldName(self):
        files={"key_": ("public_key.asc", KeyUploadServerTests.correspondentKey)}
        response = self.getPostResponse("/key_upload", files=files)
        self.assertEqual(400, response.status_code)
        
        db = email_sec_cache.Db()
        self.assertEqual(None, db.getCorrespondentKey(KeyUploadServerTests.correspondentEmailAddress))

    def testUploadInvalidKey(self):
        files={"key": ("public_key.asc", "")}
        response = self.getPostResponse("/key_upload", files=files)
        self.assertEqual(302, response.status_code)
        self.assertEqual("key_upload_error.html", response.headers["Location"])
        
        db = email_sec_cache.Db()
        self.assertEqual(None, db.getCorrespondentKey(KeyUploadServerTests.correspondentEmailAddress))
