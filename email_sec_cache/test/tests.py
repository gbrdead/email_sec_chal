# -*- coding: utf-8 -*-
import unittest
import email_sec_cache
import email
import os
import tempfile
import shutil
import logging


class Tests:
    
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
        Tests.tempDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        
        email_sec_cache.configDir = Tests.configDir
        email_sec_cache.dataDir = Tests.tempDir
        email_sec_cache.tempDir = Tests.tempDir
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
