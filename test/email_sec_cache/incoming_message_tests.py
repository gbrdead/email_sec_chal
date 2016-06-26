# -*- coding: utf-8 -*-
import unittest
import email_sec_cache
import os
import email
import test.email_sec_cache



class IncomingMessageTests(test.email_sec_cache.Tests):
    
    messagesDir = None
    correspondentEmailAddress = None
    correspondentPublicKeyFilePath = None
    
    
    @classmethod
    def setUpClass(cls):
        test.email_sec_cache.Tests.setUpClass()
        
        with open(IncomingMessageTests.correspondentPublicKeyFilePath, "r") as correspondentPublicKeyFile:
            correspondentPublicKey = correspondentPublicKeyFile.read()
        email_sec_cache.Pgp.storeCorrespondentKey(correspondentPublicKey)
        
    @classmethod
    def tearDownClass(cls):
        IncomingMessageTests.messagesDir = None
        IncomingMessageTests.correspondentEmailAddress = None
        IncomingMessageTests.correspondentPublicKeyFilePath = None
        
        test.email_sec_cache.Tests.tearDownClass()
    
    def readMessage(self, msgFileName):
        msgFilePath = os.path.join(IncomingMessageTests.messagesDir, msgFileName + ".eml")
        with open(msgFilePath, "rb") as f:
            emailMsg = email.message_from_binary_file(f)
            return email_sec_cache.IncomingMessage.create(emailMsg)



class FormatIncomingMessageTests(IncomingMessageTests):
    
    @classmethod
    def setUpClass(cls):
        if IncomingMessageTests.messagesDir is None or \
            IncomingMessageTests.correspondentEmailAddress is None or \
            IncomingMessageTests.correspondentPublicKeyFilePath is None:
            raise unittest.SkipTest("Abstract test class skipped")
        
        IncomingMessageTests.setUpClass()
        
    def readMessage(self, msgFileName):
        try:
            return IncomingMessageTests.readMessage(self, msgFileName)
        except FileNotFoundError:
            self.skipTest("Message file does not exist")
    
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
                self.assertEqual(encrypted, msgPart.encrypted)
                self.assertEqual(signed and not signedWrong, msgPart.signedAndVerified)
                
            words = email_sec_cache.extractWords(texts)
            self.assertWords(words)

    def assertWords(self, words):
        self.assertIn("Alabala", words)
        self.assertIn("Алабала", words)
        for word in words:
            self.assertIn(word, ["Alabala", "Алабала"])

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
                self.assertTrue(msgPart.forImpostor)
            words = email_sec_cache.extractWords(texts)
            self.assertWords(words)
            
    def testEncryptedWithWrongKey(self):
        with self.readMessage("encryptedWithWrongKey") as incomingMsg:
            msgParts = incomingMsg.getMessageParts()
            self.assertEqual([], msgParts)

    def testEncryptedSignedWrongSender(self):
        with self.readMessage("encrypted_signedWrongSender") as incomingMsg:
            msgParts = incomingMsg.getMessageParts()
            self.assertTrue(msgParts)
            texts = []        
            for msgPart in msgParts:
                texts += [msgPart.getPlainText()]
                self.assertFalse(msgPart.signedAndVerified)
            words = email_sec_cache.extractWords(texts)
            self.assertWords(words)



class EnigmailTests(FormatIncomingMessageTests):        
             
    @classmethod
    def setUpClass(cls):
        IncomingMessageTests.correspondentEmailAddress = "gbr@voidland.org"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.correspondentPublicKeyFilePath = os.path.join(moduleDir, "messages", "Enigmail", "correspondent_public_key.asc")
        FormatIncomingMessageTests.setUpClass()
     
     
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
     
     
     
class MailvelopeTests(FormatIncomingMessageTests):        
             
    @classmethod
    def setUpClass(cls):
        IncomingMessageTests.correspondentEmailAddress = "gbrdead@gmail.com"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.correspondentPublicKeyFilePath = os.path.join(moduleDir, "messages", "Mailvelope", "correspondent_public_key.asc")
        FormatIncomingMessageTests.setUpClass()
     
     
class MailvelopePgpInlineTests(MailvelopeTests):
              
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "Mailvelope", "PGP_Inline")
        MailvelopeTests.setUpClass()
  
  
  
class GpgOLTests(FormatIncomingMessageTests):        
          
    @classmethod
    def setUpClass(cls):
        IncomingMessageTests.correspondentEmailAddress = "gbr@voidland.org"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.correspondentPublicKeyFilePath = os.path.join(moduleDir, "messages", "GpgOL", "correspondent_public_key.asc")
        FormatIncomingMessageTests.setUpClass()
  
  
class GpgOLPgpMimeTests(GpgOLTests):
          
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "GpgOL", "PGP_MIME")
        GpgOLTests.setUpClass()
  
  
class GpgOLPgpInlineTests(GpgOLTests):
               
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "GpgOL", "PGP_Inline")
        GpgOLTests.setUpClass()
 
 
 
class GPGMailTests(FormatIncomingMessageTests):        
            
    @classmethod
    def setUpClass(cls):
        IncomingMessageTests.correspondentEmailAddress = "gbr@voidland.org"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.correspondentPublicKeyFilePath = os.path.join(moduleDir, "messages", "GPGMail", "correspondent_public_key.asc")
        FormatIncomingMessageTests.setUpClass()
    
    
class GPGMailPgpMimeTests(GPGMailTests):
            
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "GPGMail", "PGP_MIME")
        GPGMailTests.setUpClass()



class MuttTests(FormatIncomingMessageTests):        
            
    @classmethod
    def setUpClass(cls):
        IncomingMessageTests.correspondentEmailAddress = "gbr@voidland.org"
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.correspondentPublicKeyFilePath = os.path.join(moduleDir, "messages", "Mutt", "correspondent_public_key.asc")
        FormatIncomingMessageTests.setUpClass()
    
    
class MuttPgpMimeTests(MuttTests):
            
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "Mutt", "PGP_MIME")
        MuttTests.setUpClass()
      
      
class MuttPgpInlineTests(MuttTests):
             
    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages", "Mutt", "PGP_Inline")
        MuttTests.setUpClass()



class MiscMessageTests(IncomingMessageTests):

    @classmethod
    def setUpClass(cls):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        IncomingMessageTests.messagesDir = os.path.join(moduleDir, "messages")
        IncomingMessageTests.correspondentEmailAddress = "gbr@voidland.org"
        IncomingMessageTests.correspondentPublicKeyFilePath = os.path.join(moduleDir, "messages", "Enigmail", "correspondent_public_key.asc")
        IncomingMessageTests.setUpClass()


    def testMissingFromHeader(self):
        try:
            self.readMessage("missing_from_header")
            self.fail()
        except email_sec_cache.MsgException as e:
            self.assertIn("Missing From header", str(e))


    def testHtmlStripping(self):
        words = self.assertSpecialContent("html")

        self.assertNotIn("color", words)
        self.assertNotIn("var", words)

    def testMissingCharset(self):
        self.assertSpecialContent("missing_charset")

    def testNonTextMessagePart(self):
        self.assertSpecialContent("non_text_msg_part")
        
    def assertSpecialContent(self, msgFileName):
        incomingMsg = self.readMessage(msgFileName)
        msgParts = incomingMsg.getMessageParts()
        
        words = []
        for msgPart in msgParts:
            words += email_sec_cache.extractWords(msgPart.getPlainText())
            
        self.assertIn("Alabala", words)
        self.assertIn("Алабала", words)
        
        return words


    def testNonLowercaseSenderAddress(self):
        incomingMsg = self.readMessage("non_lowercase_sender_address")
        msgParts = incomingMsg.getMessageParts()
        for msgPart in msgParts:
            self.assertTrue(msgPart.signedAndVerified)
        

    def testUnknownCharset(self):
        incomingMsg = self.readMessage("unknown_charset_spam")
        incomingMsg.getMessageParts()


if __name__ == "__main__":
    unittest.main()
