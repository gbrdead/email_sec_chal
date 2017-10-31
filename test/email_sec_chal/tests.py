# -*- coding: utf-8 -*-
import logging
import os
import shutil
import tempfile
import unittest
import email_sec_chal



class Tests(unittest.TestCase):
    
    tempDir = None
    saveResourceDir = None
    saveDataDir = None
    saveTempDir = None
    

    @classmethod
    def setUpClass(cls):
        unittest.TestCase.setUpClass()
        
        logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logging.CRITICAL)
        
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        resourceDir = os.path.join(moduleDir, "res")
        
        tempDir = "/tmp/email_sec_chal" 
        if not os.access(tempDir, os.F_OK):
            os.makedirs(tempDir)
        Tests.tempDir = tempfile.mkdtemp(dir = tempDir)
        
        Tests.saveResourceDir = email_sec_chal.resourceDir
        Tests.saveDataDir = email_sec_chal.dataDir
        Tests.saveTempDir = email_sec_chal.tempDir 
        
        email_sec_chal.resourceDir = resourceDir 
        email_sec_chal.dataDir = Tests.tempDir
        email_sec_chal.tempDir = Tests.tempDir
        
        email_sec_chal.Db.initialized = False
        email_sec_chal.Db.conn = None
        
        email_sec_chal.Pgp.initialized = False
        email_sec_chal.Pgp.officialBotKeys = None
        email_sec_chal.Pgp.impostorBotKeys = None
        email_sec_chal.Pgp.botFrom = None
        email_sec_chal.Pgp.botEmailAddress = None
        email_sec_chal.Pgp.officialBotKeysFilePath = None
        

    @classmethod
    def tearDownClass(cls):
        email_sec_chal.resourceDir = Tests.saveResourceDir 
        email_sec_chal.dataDir = Tests.saveDataDir
        email_sec_chal.tempDir = Tests.saveTempDir  
        email_sec_chal.Db.initialized = False
        email_sec_chal.Pgp.initialized = False
        
        shutil.rmtree(Tests.tempDir, ignore_errors=True)
        
        unittest.TestCase.tearDownClass()
        
    @staticmethod
    def readKey(correspondentEmailAddress, correspondentKeyId, private):
        correspondentKeyFileNamePrefix = correspondentEmailAddress + " (0x" + correspondentKeyId + ")"
        correspondentPublicKeyFileName = correspondentKeyFileNamePrefix + " " + ("sec" if private else "pub") + ".asc"
        correspondentPublicKeyFilePath = os.path.join(email_sec_chal.resourceDir, correspondentPublicKeyFileName)
        with open(correspondentPublicKeyFilePath, "r") as correspondentPublicKeyFile:    
            return correspondentPublicKeyFile.read() 
    
    @staticmethod    
    def readPublicKey(correspondentEmailAddress, correspondentKeyId):
        return Tests.readKey(correspondentEmailAddress, correspondentKeyId, private=False)

    @staticmethod
    def readPrivateKey(correspondentEmailAddress, correspondentKeyId):
        return Tests.readKey(correspondentEmailAddress, correspondentKeyId, private=True)
    
    @staticmethod
    def clearDb():
        db = email_sec_chal.Db()
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM correspondents")
