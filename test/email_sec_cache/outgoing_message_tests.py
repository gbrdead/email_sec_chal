# -*- coding: utf-8 -*-
import test.email_sec_cache
import os.path
import email_sec_cache
import tempfile
import shutil
import email
import cgi



class OutgoingMessageTests(test.email_sec_cache.Tests):
    
    correspondentEmailAddress = "gbr@voidland.org" 
    correspondentKeyId = "9011E1A9"
    
    officialBotGnupgHomeDir = None
    impostorBotGnupgHomeDir = None
    correspondentGnupgHomeDir = None
    
    officialBotGpg = None
    impostorBotGpg = None
    correspondentGpg = None
    
    impostorPublicKey = None
    incomingMsg = None
    
    
    @classmethod
    def setUpClass(cls):
        test.email_sec_cache.Tests.setUpClass()
        
        officialBotKeyFilePath = os.path.join(email_sec_cache.configDir, "officialBot.asc")
        impostorBotKeyFilePath = os.path.join(email_sec_cache.configDir, "impostorBot.asc")

        correspondentKeyFileNamePrefix = OutgoingMessageTests.correspondentEmailAddress + " (0x" + OutgoingMessageTests.correspondentKeyId + ")"
        correspondentPublicKeyFileName = correspondentKeyFileNamePrefix + " pub.asc"
        correspondentPrivateKeyFileName = correspondentKeyFileNamePrefix + " sec.asc" 
        correspondentPublicKeyFilePath = os.path.join(email_sec_cache.configDir, correspondentPublicKeyFileName)
        correspondentPrivateKeyFilePath = os.path.join(email_sec_cache.configDir, correspondentPrivateKeyFileName)

        with open(officialBotKeyFilePath, "r") as officialBotKeyFile:
            officialBotKey = officialBotKeyFile.read() 
        with open(impostorBotKeyFilePath, "r") as impostorBotKeyFile:
            impostorBotKey = impostorBotKeyFile.read() 
        with open(correspondentPublicKeyFilePath, "r") as correspondentPublicKeyFile:    
            correspondentPublicKey = correspondentPublicKeyFile.read() 
        with open(correspondentPrivateKeyFilePath, "r") as correspondentPrivateKeyFile:    
            correspondentPrivateKey = correspondentPrivateKeyFile.read()
            
        with email_sec_cache.Pgp(OutgoingMessageTests.correspondentEmailAddress) as pgp:
            pgp.loadCorrespondentKey(correspondentPublicKey)
            
        OutgoingMessageTests.officialBotGnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        OutgoingMessageTests.impostorBotGnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        OutgoingMessageTests.correspondentGnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        
        OutgoingMessageTests.officialBotGpg = email_sec_cache.Pgp.createGpg(OutgoingMessageTests.officialBotGnupgHomeDir)
        OutgoingMessageTests.impostorBotGpg = email_sec_cache.Pgp.createGpg(OutgoingMessageTests.impostorBotGnupgHomeDir)
        OutgoingMessageTests.correspondentGpg = email_sec_cache.Pgp.createGpg(OutgoingMessageTests.correspondentGnupgHomeDir)
        
        OutgoingMessageTests.officialBotGpg.import_keys(officialBotKey)
        impostorFingerprints = OutgoingMessageTests.impostorBotGpg.import_keys(impostorBotKey).fingerprints
        for impostorFingerprint in impostorFingerprints:
            OutgoingMessageTests.impostorPublicKey = OutgoingMessageTests.impostorBotGpg.export_keys(impostorFingerprint)
            if OutgoingMessageTests.impostorPublicKey:
                break
        OutgoingMessageTests.correspondentGpg.import_keys(correspondentPrivateKey)
        

        moduleDir = os.path.dirname(os.path.abspath(__file__))
        validRequestFilePath = os.path.join(moduleDir, "messages", "validRequestForOfficialBot.eml")
        with open(validRequestFilePath, "rb") as validRequestFile:
            msg = email.message_from_bytes(validRequestFile.read())
            OutgoingMessageTests.incomingMsg = email_sec_cache.IncomingMessage.create(msg)

        
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(OutgoingMessageTests.officialBotGnupgHomeDir, ignore_errors=True)
        shutil.rmtree(OutgoingMessageTests.impostorBotGnupgHomeDir, ignore_errors=True)
        shutil.rmtree(OutgoingMessageTests.correspondentGnupgHomeDir, ignore_errors=True)
        
        test.email_sec_cache.Tests.tearDownClass()


    def testAsImpostorBot(self):
        with email_sec_cache.OutgoingMessage(OutgoingMessageTests.incomingMsg) as outgoingMsg:
            encryptedMsg = outgoingMsg.construct(True)
        encrypted = self.assertEncryptedMessageAndGetPayload(encryptedMsg)
        
        self.assertFalse(OutgoingMessageTests.officialBotGpg.decrypt(encrypted))
        decryptedResult = OutgoingMessageTests.impostorBotGpg.decrypt(encrypted)
        decryptedMsg = self.assertDecryptedResultAndGetMessage(decryptedResult, "impostorSpoiler.jpg")
        
        self.assertEqual(3, len(decryptedMsg.get_payload()))
        

        textMsgPart = decryptedMsg.get_payload(0)
        self.assertEqual("multipart/alternative", textMsgPart.get_content_type())
        self.assertEqual(2, len(textMsgPart.get_payload()))
        
        plainTextMsgPart = textMsgPart.get_payload(0)
        self.assertEqual("text/plain", plainTextMsgPart.get_content_type())
        text = plainTextMsgPart.get_payload(decode=True).decode(plainTextMsgPart.get_content_charset())
        self.assertIn("Alabala", text)
        self.assertIn("Алабала", text)
        self.assertNotIn("Kashkavala", text)
        self.assertNotIn("Кашкавала", text)
        
        htmlMsgPart = textMsgPart.get_payload(1)
        self.assertEqual("text/html", htmlMsgPart.get_content_type())
        html = plainTextMsgPart.get_payload(decode=True).decode(htmlMsgPart.get_content_charset())
        self.assertIn("Alabala", html)
        self.assertIn("Алабала", html)
        
        
        impostorPublicKeyAttachment = decryptedMsg.get_payload(2)
        self.assertEqual("application/pgp-keys", impostorPublicKeyAttachment.get_content_type())
        self.assertEqual("public_key.asc", impostorPublicKeyAttachment.get_filename())
        
        contentDisposition = impostorPublicKeyAttachment["Content-Disposition"]
        contentDispositionValue, _ = cgi.parse_header(contentDisposition)
        self.assertEqual("attachment", contentDispositionValue)
        
        impostorPublicKeyAttachmentCharset = impostorPublicKeyAttachment.get_content_charset() or "ascii"
        impostorPublicKey = impostorPublicKeyAttachment.get_payload(decode=True).decode(impostorPublicKeyAttachmentCharset)
        impostorPublicKey = impostorPublicKey.replace("\r\n", "\n")
        self.assertEqual(OutgoingMessageTests.impostorPublicKey, impostorPublicKey)
    
    def testAsOfficialBot(self):
        with email_sec_cache.OutgoingMessage(OutgoingMessageTests.incomingMsg) as outgoingMsg:
            encryptedMsg = outgoingMsg.construct(False)
        encrypted = self.assertEncryptedMessageAndGetPayload(encryptedMsg)
        
        self.assertFalse(OutgoingMessageTests.impostorBotGpg.decrypt(encrypted))
        decryptedResult = OutgoingMessageTests.officialBotGpg.decrypt(encrypted)
        decryptedMsg = self.assertDecryptedResultAndGetMessage(decryptedResult, "officialSpoiler.jpg")
        
        self.assertEqual(2, len(decryptedMsg.get_payload()))
        
        textMsgPart = decryptedMsg.get_payload(0)
        self.assertEqual("text/plain", textMsgPart.get_content_type())
        text = textMsgPart.get_payload(decode=True).decode(textMsgPart.get_content_charset())
        self.assertIn("Alabala", text)
        self.assertIn("Алабала", text)


    def assertEncryptedMessageAndGetPayload(self, encryptedMsg):
        self.assertEqual(OutgoingMessageTests.incomingMsg.originalMessage["From"], encryptedMsg["To"])
        self.assertEqual(OutgoingMessageTests.officialBotGpg.list_keys()[0]["uids"][0], encryptedMsg["From"])
        self.assertEqual("Re: " + OutgoingMessageTests.incomingMsg.originalMessage["Subject"], encryptedMsg["Subject"])
        
        self.assertEqual("multipart/encrypted", encryptedMsg.get_content_type())
        self.assertEqual("application/pgp-encrypted", encryptedMsg.get_param("protocol"))
        
        payload = encryptedMsg.get_payload()
        self.assertEqual(2, len(payload))
        pgpIdentification = payload[0]
        encryptedAsc = payload[1]
        
        self.assertEqual("application/pgp-encrypted", pgpIdentification.get_content_type())
        pgpIdentificationCharset = pgpIdentification.get_content_charset() or "ascii"
        self.assertEqual("Version: 1\n", pgpIdentification.get_payload(decode=True).decode(pgpIdentificationCharset))
        
        self.assertEqual("application/octet-stream", encryptedAsc.get_content_type())
        encryptedAscCharset = encryptedAsc.get_content_charset() or "ascii"
        encrypted = encryptedAsc.get_payload(decode=True).decode(encryptedAscCharset)
        
        self.assertTrue(OutgoingMessageTests.correspondentGpg.decrypt(encrypted))

        return encrypted
    
    def assertDecryptedResultAndGetMessage(self, decryptedResult, spoilerPictureFileName):
        self.assertTrue(decryptedResult)
        self.assertTrue(decryptedResult.valid)
        decryptedMsg = email.message_from_bytes(decryptedResult.data)
        
        self.assertEqual("multipart/mixed", decryptedMsg.get_content_type())
        self.assertLessEqual(2, len(decryptedMsg.get_payload()))
        
        spoilerPictureAttachment = decryptedMsg.get_payload(1)
        self.assertEqual("image/jpeg", spoilerPictureAttachment.get_content_type())
        self.assertEqual("spoiler.jpg", spoilerPictureAttachment.get_filename())
        
        contentDisposition = spoilerPictureAttachment["Content-Disposition"]
        contentDispositionValue, _ = cgi.parse_header(contentDisposition)
        self.assertEqual("attachment", contentDispositionValue)
        
        spoilerFilePath = os.path.join(email_sec_cache.configDir, spoilerPictureFileName)
        with open(spoilerFilePath, "rb") as spoilerFile:
            expectedSpoilerPictureData = spoilerFile.read()    
        self.assertEqual(expectedSpoilerPictureData, spoilerPictureAttachment.get_payload(decode=True))
        
        return decryptedMsg
