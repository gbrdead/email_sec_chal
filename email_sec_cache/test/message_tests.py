# -*- coding: utf-8 -*-
import unittest
import email_sec_cache
import logging
import os
import tempfile
import shutil
import email



class IncomingMessageTests(unittest.TestCase):
    
    messagesDir = None
    senderEmailAddress = None
    correspondentPublicKeyFileName = None
    
    tempDir = None
    saveConfigDir = None
    saveDataDir = None
    saveTempDir = None

    
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logging.INFO)
        
        if IncomingMessageTests.messagesDir is None or \
            IncomingMessageTests.senderEmailAddress is None or \
            IncomingMessageTests.correspondentPublicKeyFileName is None:
            raise unittest.SkipTest("Abstract test class skipped")
        
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        configDir = os.path.join(moduleDir, "config")
        
        if not os.access(email_sec_cache.tempDir, os.F_OK):
            os.makedirs(email_sec_cache.tempDir)
        IncomingMessageTests.tempDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        
        IncomingMessageTests.saveConfigDir = email_sec_cache.configDir
        IncomingMessageTests.saveDataDir = email_sec_cache.dataDir
        IncomingMessageTests.saveTempDir = email_sec_cache.tempDir 
        
        email_sec_cache.configDir = configDir 
        email_sec_cache.dataDir = IncomingMessageTests.tempDir
        email_sec_cache.tempDir = IncomingMessageTests.tempDir
        email_sec_cache.Db.initialized = False
        email_sec_cache.Pgp.initialized = False
        
        with open(IncomingMessageTests.correspondentPublicKeyFileName, "r") as correspondentPublicKeyFile:
            correspondentKey = correspondentPublicKeyFile.read()
            with email_sec_cache.Pgp(IncomingMessageTests.senderEmailAddress) as pgp:
                pgp.loadCorrespondentKey(correspondentKey)
        
    @classmethod
    def tearDownClass(cls):
        email_sec_cache.configDir = IncomingMessageTests.saveConfigDir 
        email_sec_cache.dataDir = IncomingMessageTests.saveDataDir
        email_sec_cache.tempDir = IncomingMessageTests.saveTempDir  
        email_sec_cache.Db.initialized = False
        email_sec_cache.Pgp.initialized = False
        
        shutil.rmtree(IncomingMessageTests.tempDir, ignore_errors=True)
        IncomingMessageTests.messagesDir = None
        IncomingMessageTests.senderEmailAddress = None
        IncomingMessageTests.correspondentPublicKeyFileName = None
    
    def getMessageFileName(self, encrypted, signed, signedWrong, plain, html, attachments):
        if encrypted:
            fileName = "encrypted"
        else:
            fileName = "unencrypted"
        if signed:
            fileName += "_signed"
            if signedWrong:
                fileName += "Wrong"
        else:
            fileName += "_unsigned"
        if plain:
            fileName += "_plain"
        if html:
            fileName += "_html"
        if attachments:
            fileName += "_attachments"
        return fileName
    
    def readMessage(self, msgFileName):
        msgFilePath = os.path.join(self.messagesDir, msgFileName + ".eml")
        if not os.access(msgFilePath, os.F_OK):
            self.skipTest("Message file does not exist")
        with open(msgFilePath, "rb") as f:
            emailMsg = email.message_from_binary_file(f)
            return email_sec_cache.IncomingMessage.create(emailMsg)
    
    def readMessageByAttributes(self, encrypted, signed, signedWrong, plain, html, attachments):
        msgFileName = self.getMessageFileName(encrypted, signed, signedWrong, plain, html, attachments)
        return self.readMessage(msgFileName)
        
    def assertMessage(self, encrypted, signed, signedWrong, plain, html, attachments):
        with self.readMessageByAttributes(encrypted, signed, signedWrong, plain, html, attachments) as incomingMsg:
            msgParts = incomingMsg.getMessageParts()
            self.assertTrue(msgParts)
    
            texts = []        
            for msgPart in msgParts:
                texts += [msgPart.getPlainText()]
                self.assertEqual(encrypted, msgPart.isEncrypted)
                self.assertEqual(signed and not signedWrong, msgPart.isVerified)
                
            words = email_sec_cache.extractWords(texts)
            self.assertIn("Alabala", words)
            self.assertIn("Алабала", words)
            # The attachments should be ignored, even if containing text.
            self.assertNotIn("Portokala", words)
            self.assertNotIn("Портокала", words)
            self.assertNotIn("Kashkavala", words)
            self.assertNotIn("Кашкавала", words)
        

    def testUnencryptedUnsignedPlain(self):
        encrypted = False
        signed = False
        signedWrong = False
        plain = True
        html = False
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)
        
    def testEncryptedUnsignedPlain(self):
        encrypted = True
        signed = False
        signedWrong = False
        plain = True
        html = False
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedPlain(self):
        encrypted = False
        signed = True
        signedWrong = False
        plain = True
        html = False
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedPlain(self):
        encrypted = True
        signed = True
        signedWrong = False
        plain = True
        html = False
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedWrongPlain(self):
        encrypted = False
        signed = True
        signedWrong = True
        plain = True
        html = False
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedWrongPlain(self):
        encrypted = True
        signed = True
        signedWrong = True
        plain = True
        html = False
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedUnsignedHtml(self):
        encrypted = False
        signed = False
        signedWrong = False
        plain = False
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)
        
    def testEncryptedUnsignedHtml(self):
        encrypted = True
        signed = False
        signedWrong = False
        plain = False
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedHtml(self):
        encrypted = False
        signed = True
        signedWrong = False
        plain = False
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedHtml(self):
        encrypted = True
        signed = True
        signedWrong = False
        plain = False
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedWrongHtml(self):
        encrypted = False
        signed = True
        signedWrong = True
        plain = False
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedWrongHtml(self):
        encrypted = True
        signed = True
        signedWrong = True
        plain = False
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedUnsignedPlainHtml(self):
        encrypted = False
        signed = False
        signedWrong = False
        plain = True
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)
        
    def testEncryptedUnsignedPlainHtml(self):
        encrypted = True
        signed = False
        signedWrong = False
        plain = True
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedPlainHtml(self):
        encrypted = False
        signed = True
        signedWrong = False
        plain = True
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedPlainHtml(self):
        encrypted = True
        signed = True
        signedWrong = False
        plain = True
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedWrongPlainHtml(self):
        encrypted = False
        signed = True
        signedWrong = True
        plain = True
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedWrongPlainHtml(self):
        encrypted = True
        signed = True
        signedWrong = True
        plain = True
        html = True
        attachments = False
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedUnsignedPlainAttachments(self):
        encrypted = False
        signed = False
        signedWrong = False
        plain = True
        html = False
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)
        
    def testEncryptedUnsignedPlainAttachments(self):
        encrypted = True
        signed = False
        signedWrong = False
        plain = True
        html = False
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedPlainAttachments(self):
        encrypted = False
        signed = True
        signedWrong = False
        plain = True
        html = False
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedPlainAttachments(self):
        encrypted = True
        signed = True
        signedWrong = False
        plain = True
        html = False
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedWrongPlainAttachments(self):
        encrypted = False
        signed = True
        signedWrong = True
        plain = True
        html = False
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedWrongPlainAttachments(self):
        encrypted = True
        signed = True
        signedWrong = True
        plain = True
        html = False
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedUnsignedHtmlAttachments(self):
        encrypted = False
        signed = False
        signedWrong = False
        plain = False
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)
        
    def testEncryptedUnsignedHtmlAttachments(self):
        encrypted = True
        signed = False
        signedWrong = False
        plain = False
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedHtmlAttachments(self):
        encrypted = False
        signed = True
        signedWrong = False
        plain = False
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedHtmlAttachments(self):
        encrypted = True
        signed = True
        signedWrong = False
        plain = False
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedWrongHtmlAttachments(self):
        encrypted = False
        signed = True
        signedWrong = True
        plain = False
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedWrongHtmlAttachments(self):
        encrypted = True
        signed = True
        signedWrong = True
        plain = False
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedUnsignedPlainHtmlAttachments(self):
        encrypted = False
        signed = False
        signedWrong = False
        plain = True
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)
        
    def testEncryptedUnsignedPlainHtmlAttachments(self):
        encrypted = True
        signed = False
        signedWrong = False
        plain = True
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedPlainHtmlAttachments(self):
        encrypted = False
        signed = True
        signedWrong = False
        plain = True
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedPlainHtmlAttachments(self):
        encrypted = True
        signed = True
        signedWrong = False
        plain = True
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testUnencryptedSignedWrongPlainHtmlAttachments(self):
        encrypted = False
        signed = True
        signedWrong = True
        plain = True
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)

    def testEncryptedSignedWrongPlainHtmlAttachments(self):
        encrypted = True
        signed = True
        signedWrong = True
        plain = True
        html = True
        attachments = True
        self.assertMessage(encrypted, signed, signedWrong, plain, html, attachments)
        
    def testEncryptedForImpostor(self):
        with self.readMessage("encryptedForImpostor") as incomingMsg:
            msgParts = incomingMsg.getMessageParts()
            self.assertTrue(msgParts)
            texts = []        
            for msgPart in msgParts:
                texts += [msgPart.getPlainText()]
                self.assertTrue(msgPart.isForImpostor)
            words = email_sec_cache.extractWords(texts)
            self.assertIn("Alabala", words)
            self.assertIn("Алабала", words)
            
    def testEncryptedWithWrongKey(self):
        try:
            with self.readMessage("encryptedWithWrongKey") as incomingMsg:
                incomingMsg.getMessageParts()
            self.fail()
        except email_sec_cache.PgpException as e:
            self.assertIn("secret key not available", str(e))            

    def testEncryptedSignedWrongSender(self):
        with self.readMessage("encrypted_signedWrongSender") as incomingMsg:
            msgParts = incomingMsg.getMessageParts()
            self.assertTrue(msgParts)
            texts = []        
            for msgPart in msgParts:
                texts += [msgPart.getPlainText()]
                self.assertFalse(msgPart.isVerified)
            words = email_sec_cache.extractWords(texts)
            self.assertIn("Alabala", words)
            self.assertIn("Алабала", words)



class EnigmailTests(IncomingMessageTests):        
        
    @classmethod
    def setUpClass(cls):
        IncomingMessageTests.senderEmailAddress = "gbr@voidland.org"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.correspondentPublicKeyFileName = os.path.join(moduleDir, "messages", "Enigmail", "correspondent_public_key.asc")
        IncomingMessageTests.setUpClass()


class EnigmailPgpMimeTests(EnigmailTests):
        
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "Enigmail", "PGP_MIME")
        EnigmailTests.setUpClass()
  
  
class EnigmailPgpInlineTests(EnigmailTests):
        
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "Enigmail", "PGP_Inline")
        EnigmailTests.setUpClass()



class MailvelopeTests(IncomingMessageTests):        
        
    @classmethod
    def setUpClass(cls):
        IncomingMessageTests.senderEmailAddress = "gbrdead@gmail.com"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.correspondentPublicKeyFileName = os.path.join(moduleDir, "messages", "Mailvelope", "correspondent_public_key.asc")
        IncomingMessageTests.setUpClass()


class MailvelopePgpInlineTests(MailvelopeTests):
        
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "Mailvelope", "PGP_Inline")
        MailvelopeTests.setUpClass()



if __name__ == "__main__":
    unittest.main()
