# -*- coding: utf-8 -*-
import logging
import os
import shutil
import tempfile
import unittest
import email_sec_cache



class Tests(unittest.TestCase):
    
    tempDir = None
    saveConfigDir = None
    saveDataDir = None
    saveTempDir = None
    

    @classmethod
    def setUpClass(cls):
        unittest.TestCase.setUpClass()
        
        logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logging.ERROR)
        
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        configDir = os.path.join(moduleDir, "config")
        
        if not os.access(email_sec_cache.tempDir, os.F_OK):
            os.makedirs(email_sec_cache.tempDir)
        Tests.tempDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        
        Tests.saveConfigDir = email_sec_cache.configDir
        Tests.saveDataDir = email_sec_cache.dataDir
        Tests.saveTempDir = email_sec_cache.tempDir 
        
        email_sec_cache.configDir = configDir 
        email_sec_cache.dataDir = Tests.tempDir
        email_sec_cache.tempDir = Tests.tempDir
        email_sec_cache.Db.initialized = False
        email_sec_cache.Pgp.initialized = False

    @classmethod
    def tearDownClass(cls):
        email_sec_cache.configDir = Tests.saveConfigDir 
        email_sec_cache.dataDir = Tests.saveDataDir
        email_sec_cache.tempDir = Tests.saveTempDir  
        email_sec_cache.Db.initialized = False
        email_sec_cache.Pgp.initialized = False
        
        shutil.rmtree(Tests.tempDir, ignore_errors=True)
        
        unittest.TestCase.tearDownClass()
        
    @staticmethod
    def readKey(correspondentEmailAddress, correspondentKeyId, private):
        correspondentKeyFileNamePrefix = correspondentEmailAddress + " (0x" + correspondentKeyId + ")"
        correspondentPublicKeyFileName = correspondentKeyFileNamePrefix + " " + ("sec" if private else "pub") + ".asc"
        correspondentPublicKeyFilePath = os.path.join(email_sec_cache.configDir, correspondentPublicKeyFileName)
        with open(correspondentPublicKeyFilePath, "r") as correspondentPublicKeyFile:    
            return correspondentPublicKeyFile.read() 
    
    @staticmethod    
    def readPublicKey(correspondentEmailAddress, correspondentKeyId):
        return Tests.readKey(correspondentEmailAddress, correspondentKeyId, private=False)

    @staticmethod
    def readPrivateKey(correspondentEmailAddress, correspondentKeyId):
        return Tests.readKey(correspondentEmailAddress, correspondentKeyId, private=True)



class PgpTests(Tests):
    
    correspondentEmailAddress = "gbr@voidland.org" 
    correspondentKeyId = "9011E1A9"
    correspondentKeyAltId = "345933AF"
    
        
    def testWrongKeyForEmailAddress(self):
        correspondentKey = Tests.readPublicKey(PgpTests.correspondentEmailAddress, PgpTests.correspondentKeyId)
            
        emailAddress = "a" + PgpTests.correspondentEmailAddress
        try:
            with email_sec_cache.Pgp(emailAddress) as pgp:
                pgp.loadCorrespondentKey(correspondentKey)
            self.fail()
        except email_sec_cache.PgpException as e:
            self.assertIn(("No correspondent key for email address %s found." % emailAddress), str(e))
             
    def testLoadNewCorrespondentKey(self):
        correspondentKey = Tests.readPublicKey(PgpTests.correspondentEmailAddress, PgpTests.correspondentKeyId)
        correspondentKeyAlt = Tests.readPublicKey(PgpTests.correspondentEmailAddress, PgpTests.correspondentKeyAltId)
            
        with email_sec_cache.Pgp(PgpTests.correspondentEmailAddress) as pgp:
            pgp.loadCorrespondentKey(correspondentKey)
            self.assertEqual(["44EDCA862A2D87BDB1D9C36B7FB049F79011E1A9"], pgp.correspondentFingerprints)
            pgp.loadCorrespondentKey(correspondentKeyAlt)
            self.assertEqual(["8D73455FF0373B363B719A35C97A6EF5345933AF"], pgp.correspondentFingerprints)
            
    def testLoadInvalidCorrespondentKey(self):
        for garbageKey in ["", "garbage"]:
            try:
                with email_sec_cache.Pgp(PgpTests.correspondentEmailAddress) as pgp:
                    pgp.loadCorrespondentKey(garbageKey)
                self.fail()
            except email_sec_cache.PgpException as e:
                self.assertIn(("No correspondent key for email address %s found." % PgpTests.correspondentEmailAddress), str(e))
