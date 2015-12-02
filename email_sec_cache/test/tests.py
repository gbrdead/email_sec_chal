# -*- coding: utf-8 -*-
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
        return email_sec_cache.Message(msg)
    
    def assertParsedMessage(self, parsedMsg, encryptedExpected, signedExpected):
        self.assertEqual(encryptedExpected, parsedMsg.isEncrypted)
        self.assertEqual(signedExpected, parsedMsg.isVerified)
        words = email_sec_cache.extractWords(parsedMsg.getMessageTexts())
        self.assertIn("Alabala", words)
        self.assertIn(u"Алабала", words)


    def testEncryptedWrong(self):
        try:
            self.parseMessage(True, False, wrongEncryptionKey = True, plaintext = True)
            self.fail()
        except email_sec_cache.PgpException as e:
            self.assertIn("secret key not available", str(e))

    
    def testUnencryptedUnsignedPlaintext(self):
        encrypted = False
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)
                    
    def testUnencryptedSignedPlaintext(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testEncryptedUnsignedPlaintext(self):
        encrypted = True
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)
                    
    def testEncryptedSignedPlaintext(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testUnencryptedSignedWrongPlaintext(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)

    def testEncryptedSignedWrongPlaintext(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)


    def testUnencryptedUnsignedPlaintextHtml(self):
        encrypted = False
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)
                    
    def testUnencryptedSignedPlaintextHtml(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testEncryptedUnsignedPlaintextHtml(self):
        encrypted = True
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)        
                    
    def testEncryptedSignedPlaintextHtml(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testUnencryptedSignedWrongPlaintextHtml(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)

    def testEncryptedSignedWrongPlaintextHtml(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)


    def testUnencryptedUnsignedHtml(self):
        encrypted = False
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)
                    
    def testUnencryptedSignedHtml(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testEncryptedUnsignedHtml(self):
        encrypted = True
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)
                    
    def testEncryptedSignedHtml(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testUnencryptedSignedWrongHtml(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)
        
    def testEncryptedSignedWrongHtml(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)


    def testUnencryptedUnsignedAttachment(self):
        encrypted = False
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)
                    
    def testUnencryptedSignedAttachment(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testEncryptedUnsignedAttachment(self):
        encrypted = True
        signed = False
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)
                    
    def testEncryptedSignedAttachment(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, plaintext = True, attachment = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed)

    def testUnencryptedSignedWrongAttachment(self):
        encrypted = False
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, attachment = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)

    def testEncryptedSignedWrongAttachment(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongSignatureKey = True, plaintext = True, attachment = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)


if __name__ == "__main__":
    unittest.main()
