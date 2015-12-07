# -*- coding: utf-8 -*-
import unittest
import email_sec_cache
import email
import os
import tempfile
import shutil
import logging


class Tests(unittest.TestCase):
    
    pgp = None
    tempDir = None
    

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(format=u"%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logging.DEBUG)
        
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        configDir = os.path.join(moduleDir, u"config")
        
        if not os.access(email_sec_cache.tempDir, os.F_OK):
            os.makedirs(email_sec_cache.tempDir)
        Tests.tempDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        
        email_sec_cache.configDir = configDir
        email_sec_cache.dataDir = Tests.tempDir
        email_sec_cache.tempDir = Tests.tempDir
        email_sec_cache.Pgp.initialized = False
        
        Tests.pgp = email_sec_cache.Pgp(u"gbr@voidland.org")
        
        with open(os.path.join(configDir, u"correspondent.asc"), "r") as correspondentKeyFile:
            correspondentKey = correspondentKeyFile.read()
        Tests.pgp.loadCorrespondentKey(correspondentKey)
    
    @classmethod
    def tearDownClass(cls):
        Tests.pgp.close()
        shutil.rmtree(Tests.tempDir, ignore_errors=True)
        

    def getMessageFilePath(self, encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, plaintext, html, attachment):
        if encrypted:
            fileName = u"encrypted"
            if wrongEncryptionKey:
                fileName += u"Wrong"
            if forImpostor:
                fileName += u"ForImpostor"
        else:
            fileName = u"unencrypted"
        if signed:
            fileName += u"_signed"
            if wrongSignatureKey:
                fileName += u"Wrong"
        else:
            fileName += u"_unsigned"
        if plaintext:
            fileName += u"_plaintext"
        if html:
            fileName += u"_html"
        if attachment:
            fileName += u"_attachment"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        msgDir = os.path.join(moduleDir, u"messages")             
        return os.path.join(msgDir, fileName + u".msg")
    
    def getMessage(self, encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, plaintext, html, attachment):
        with open(self.getMessageFilePath(encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, plaintext, html, attachment), "r") as f:
            return email.message_from_file(f)
        
    def parseMessage(self, encrypted, signed, wrongEncryptionKey = False, wrongSignatureKey = False, forImpostor = False, plaintext = False, html = False, attachment = False):
        msg = self.getMessage(encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, plaintext, html, attachment)
        return email_sec_cache.IncomingMessage(msg)
    
    def assertParsedMessage(self, parsedMsg, encryptedExpected, signedExpected, forImpostorExpected = False):
        self.assertEqual(encryptedExpected, parsedMsg.isEncrypted)
        self.assertEqual(signedExpected, parsedMsg.isVerified)
        if parsedMsg.isEncrypted:
            self.assertEqual(forImpostorExpected, parsedMsg.isForImpostor)
        words = email_sec_cache.extractWords(parsedMsg.getMessageTexts())
        self.assertIn(u"Alabala", words)
        self.assertIn(u"Алабала", words)


    def testEncryptedWrongKey(self):
        try:
            self.parseMessage(True, False, wrongEncryptionKey = True, plaintext = True)
            self.fail()
        except email_sec_cache.PgpException as e:
            self.assertIn(u"secret key not available", unicode(e))

    def testEncryptedWrongSender(self):
        encrypted = True
        signed = True
        parsedMsg = self.parseMessage(encrypted, signed, wrongEncryptionKey = True, html = True)
        self.assertParsedMessage(parsedMsg, encrypted, False)

    
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

    def testEncryptedForImpostorSignedAttachment(self):
        encrypted = True
        signed = True
        forImpostor = True
        parsedMsg = self.parseMessage(encrypted, signed, forImpostor = forImpostor, plaintext = True, attachment = True)
        self.assertParsedMessage(parsedMsg, encrypted, signed, forImpostor)


if __name__ == "__main__":
    unittest.main()
