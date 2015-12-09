# -*- coding: utf-8 -*-
import unittest
import email_sec_cache
import email
import os
import tempfile
import shutil
import logging


class Tests(unittest.TestCase):
    
    tempDir = None
    senderEmailAddress = u"gbr@voidland.org"
    configDir = None
    correspondentKey = None
    

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(format=u"%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logging.INFO)
        
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        Tests.configDir = os.path.join(moduleDir, u"config")
        
        if not os.access(email_sec_cache.tempDir, os.F_OK):
            os.makedirs(email_sec_cache.tempDir)
        MessageTests.tempDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        
        email_sec_cache.configDir = Tests.configDir
        email_sec_cache.dataDir = MessageTests.tempDir
        email_sec_cache.tempDir = MessageTests.tempDir
        email_sec_cache.Db.initialized = False
        email_sec_cache.Pgp.initialized = False
        
        with open(os.path.join(email_sec_cache.configDir, u"correspondent.asc"), "r") as correspondentKeyFile:
            Tests.correspondentKey = correspondentKeyFile.read()
        
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MessageTests.tempDir, ignore_errors=True)
        
    def readMessage(self, fileName):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        msgDir = os.path.join(moduleDir, u"messages")             
        msgFilePath = os.path.join(msgDir, fileName + u".msg")
        with open(msgFilePath, "r") as f:
            return email.message_from_file(f)



class MessageTests(Tests):

    @classmethod
    def setUpClass(cls):
        Tests.setUpClass()
        
        with email_sec_cache.Pgp(MessageTests.senderEmailAddress) as pgp:
            pgp.loadCorrespondentKey(Tests.correspondentKey)
    
    @classmethod
    def tearDownClass(cls):
        Tests.tearDownClass()
        

    def getMessageFileName(self, encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, wrongSender, plaintext, html, attachment):
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
        if wrongSender:
            fileName += u"_WrongSender"
        return fileName
    
    def getMessage(self, encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, wrongSender, plaintext, html, attachment):
        return self.readMessage(self.getMessageFileName(encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, wrongSender, plaintext, html, attachment))
        
    def parseMessage(self, encrypted, signed, wrongEncryptionKey = False, wrongSignatureKey = False, forImpostor = False, wrongSender = False, plaintext = False, html = False, attachment = False):
        msg = self.getMessage(encrypted, signed, wrongEncryptionKey, wrongSignatureKey, forImpostor, wrongSender, plaintext, html, attachment)
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
        parsedMsg = self.parseMessage(encrypted, signed, wrongSender = True, html = True)
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

        
    def testMissingFromHeader(self):
        try:
            email_sec_cache.IncomingMessage(self.readMessage(u"missing_from_header"))
            self.fail()
        except email_sec_cache.MsgException as e:
            self.assertIn(u"Missing From header", unicode(e))

    def testHtmlStripping(self):
        parsedMsg = email_sec_cache.IncomingMessage(self.readMessage(u"html"))
        words = email_sec_cache.extractWords(parsedMsg.getMessageTexts())
        self.assertIn(u"Alabala", words)
        self.assertIn(u"Алабала", words)
        self.assertNotIn(u"html", words)
        self.assertNotIn(u"color", words)
        self.assertNotIn(u"var", words)
        
    
        
class PgpTests(Tests):
        
    @classmethod
    def setUpClass(cls):
        Tests.setUpClass()
    
    @classmethod
    def tearDownClass(cls):
        Tests.tearDownClass()


    def testWrongKeyForEmailAddress(self):
        emailAddress = u"a" + Tests.senderEmailAddress
        try:
            with email_sec_cache.Pgp(emailAddress) as pgp:
                pgp.loadCorrespondentKey(Tests.correspondentKey)
            self.fail()
        except email_sec_cache.PgpException as e:
            self.assertIn((u"No correspondent key for email address %s found." % emailAddress), unicode(e))
             
    def testLoadNewCorrespondentKey(self):
        with open(os.path.join(email_sec_cache.configDir, u"correspondent_alt.asc"), "r") as correspondentKeyFile:
            correspondentKeyAlt = correspondentKeyFile.read()
        with email_sec_cache.Pgp(Tests.senderEmailAddress) as pgp:
            pgp.loadCorrespondentKey(Tests.correspondentKey)
            self.assertEqual(["44EDCA862A2D87BDB1D9C36B7FB049F79011E1A9"], pgp.correspondentFingerprints)
            pgp.loadCorrespondentKey(correspondentKeyAlt)
            self.assertEqual(["8D73455FF0373B363B719A35C97A6EF5345933AF"], pgp.correspondentFingerprints)

    def testWrongSender(self):
        with email_sec_cache.Pgp(Tests.senderEmailAddress) as pgp:
            try:
                pgp.parseMessage(self.readMessage(u"encrypted_signed_html_WrongSender"))
                self.fail()
            except email_sec_cache.PgpException as e:
                self.assertIn(u"Wrong sender", unicode(e))
                
    def testMissingFromHeader(self):
        with email_sec_cache.Pgp(Tests.senderEmailAddress) as pgp:
            try:
                pgp.parseMessage(self.readMessage(u"missing_from_header"))
                self.fail()
            except email_sec_cache.PgpException as e:
                self.assertIn(u"Missing From header", unicode(e))



if __name__ == "__main__":
    unittest.main()
