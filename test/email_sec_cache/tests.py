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
        resourceDir = os.path.join(moduleDir, "config")
        
        tempDir = "/tmp/email_sec_cache" 
        if not os.access(tempDir, os.F_OK):
            os.makedirs(tempDir)
        Tests.tempDir = tempfile.mkdtemp(dir = tempDir)
        
        Tests.saveConfigDir = email_sec_cache.resourceDir
        Tests.saveDataDir = email_sec_cache.dataDir
        Tests.saveTempDir = email_sec_cache.tempDir 
        
        email_sec_cache.resourceDir = resourceDir 
        email_sec_cache.dataDir = Tests.tempDir
        email_sec_cache.tempDir = Tests.tempDir
        email_sec_cache.Db.initialized = False
        email_sec_cache.Pgp.initialized = False

    @classmethod
    def tearDownClass(cls):
        email_sec_cache.resourceDir = Tests.saveConfigDir 
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
        correspondentPublicKeyFilePath = os.path.join(email_sec_cache.resourceDir, correspondentPublicKeyFileName)
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
    
        
    def testStoreNewCorrespondentKey(self):
        correspondentKey = Tests.readPublicKey(PgpTests.correspondentEmailAddress, PgpTests.correspondentKeyId)
        correspondentKeyAlt = Tests.readPublicKey(PgpTests.correspondentEmailAddress, PgpTests.correspondentKeyAltId)
        
        email_sec_cache.Pgp.storeCorrespondentKey(correspondentKey)
        with email_sec_cache.Pgp(PgpTests.correspondentEmailAddress) as pgp:
            self.assertEqual(["44EDCA862A2D87BDB1D9C36B7FB049F79011E1A9"], pgp.correspondentFingerprints)

        email_sec_cache.Pgp.storeCorrespondentKey(correspondentKeyAlt)
        with email_sec_cache.Pgp(PgpTests.correspondentEmailAddress) as pgp:
            self.assertEqual(["8D73455FF0373B363B719A35C97A6EF5345933AF"], pgp.correspondentFingerprints)
            
    def testLoadInvalidCorrespondentKeys(self):
        db = email_sec_cache.Db()
        initialCorrespondentsCount = db.getCorrespondentsCount()
        for garbageKey in ["", "garbage"]:
            emailAddresses = email_sec_cache.Pgp.storeCorrespondentKey(garbageKey)
            self.assertListEqual([], emailAddresses)
            self.assertEqual(initialCorrespondentsCount, db.getCorrespondentsCount())
