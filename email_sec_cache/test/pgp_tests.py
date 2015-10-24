import unittest
import email_sec_cache
import email
import os
import tempfile
import shutil


class PgpTests(unittest.TestCase):
    
    pgp = None
    tempDir = None
    

    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        configDir = os.path.join(moduleDir, "config")
        
        if not os.access(email_sec_cache.Pgp.tempDir, os.F_OK):
            os.makedirs(email_sec_cache.Pgp.tempDir)
        PgpTests.tempDir = tempfile.mkdtemp(dir = email_sec_cache.Pgp.tempDir)
        
        email_sec_cache.Pgp.configDir = configDir
        email_sec_cache.Pgp.dataDir = PgpTests.tempDir
        email_sec_cache.Pgp.tempDir = PgpTests.tempDir
        email_sec_cache.Pgp.initialized = False
        
        PgpTests.pgp = email_sec_cache.Pgp("gbr@voidland.org")
        
        with open(os.path.join(configDir, "correspondent.asc"), "r") as correspondentKeyFile:
            correspondentKey = correspondentKeyFile.read()
        PgpTests.pgp.loadCorrespondentKey(correspondentKey)
    
    @classmethod
    def tearDownClass(cls):
        PgpTests.pgp.close()
        shutil.rmtree(PgpTests.tempDir, ignore_errors=True)
        

    def getMessageFilePath(self, encrypted, signed, wrongEncryptionKey, wrongSignatureKey, plaintext, html, attachment):
        if encrypted:
            fileName = "encrypted"
            if wrongEncryptionKey:
                fileName += "Wrong"
        else:
            fileName = "unencrypted"
        if signed:
            fileName += "_signed"
            if wrongSignatureKey:
                fileName += "Wrong"
        else:
            fileName += "_unsigned"
        if plaintext:
            fileName += "_plaintext"
        if html:
            fileName += "_html"
        if attachment:
            fileName += "_attachment"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        msgDir = os.path.join(moduleDir, "messages")             
        return os.path.join(msgDir, fileName + ".msg")
    
    def getMessage(self, encrypted, signed, wrongEncryptionKey, wrongSignatureKey, plaintext, html, attachment):
        with open(self.getMessageFilePath(encrypted, signed, wrongEncryptionKey, wrongSignatureKey, plaintext, html, attachment), "r") as f:
            return email.message_from_file(f)
        
    def parseMessage(self, encrypted, signed, wrongEncryptionKey = False, wrongSignatureKey = False, plaintext = False, html = False, attachment = False):
        msg = self.getMessage(encrypted, signed, wrongEncryptionKey, wrongSignatureKey, plaintext, html, attachment)
        isEncrypted, isVerified, plainMsg = PgpTests.pgp.parseMessage(msg)
        return isEncrypted, isVerified, plainMsg


    def testEncryptedWrong(self):
        try:
            self.parseMessage(True, False, wrongEncryptionKey = True, plaintext = True)
            self.fail()
        except email_sec_cache.PgpException as e:
            self.assertIn("secret key not available", str(e))

    
    def testUnencryptedUnsignedPlaintext(self):
        encrypted = False
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testUnencryptedSignedPlaintext(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified)

    def testEncryptedUnsignedPlaintext(self):
        encrypted = True
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testEncryptedSignedPlaintext(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 

    def testUnencryptedSignedWrongPlaintext(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 

    def testEncryptedSignedWrongPlaintext(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 


    def testUnencryptedUnsignedPlaintextHtml(self):
        encrypted = False
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testUnencryptedSignedPlaintextHtml(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 

    def testEncryptedUnsignedPlaintextHtml(self):
        encrypted = True
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testEncryptedSignedPlaintextHtml(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 

    def testUnencryptedSignedWrongPlaintextHtml(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 

    def testEncryptedSignedWrongPlaintextHtml(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 


    def testUnencryptedUnsignedHtml(self):
        encrypted = False
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testUnencryptedSignedHtml(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 

    def testEncryptedUnsignedHtml(self):
        encrypted = True
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testEncryptedSignedHtml(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 

    def testUnencryptedSignedWrongHtml(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 

    def testEncryptedSignedWrongHtml(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, html = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 


    def testUnencryptedUnsignedAttachment(self):
        encrypted = False
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testUnencryptedSignedAttachment(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 

    def testEncryptedUnsignedAttachment(self):
        encrypted = True
        signed = False
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 
                    
    def testEncryptedSignedAttachment(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(signed, isVerified) 

    def testUnencryptedSignedWrongAttachment(self):
        encrypted = False
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, attachment = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 

    def testEncryptedSignedWrongAttachment(self):
        encrypted = True
        signed = True
        isEncrypted, isVerified, plainMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, attachment = True)
        self.assertEqual(encrypted, isEncrypted)
        self.assertEqual(False, isVerified) 


if __name__ == "__main__":
    unittest.main()
