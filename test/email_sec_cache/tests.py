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
        
        logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logging.INFO)
        
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



class PgpTests(Tests):
        
    def testWrongKeyForEmailAddress(self):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        keysDir = os.path.join(moduleDir, "messages", "Enigmail")
        with open(os.path.join(keysDir, "correspondent_public_key.asc"), "r") as correspondentKeyFile:
            correspondentKey = correspondentKeyFile.read()
            
        emailAddress = "gbr_@voidland.org"
        try:
            with email_sec_cache.Pgp(emailAddress) as pgp:
                pgp.loadCorrespondentKey(correspondentKey)
            self.fail()
        except email_sec_cache.PgpException as e:
            self.assertIn(("No correspondent key for email address %s found." % emailAddress), str(e))
             
    def testLoadNewCorrespondentKey(self):
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        keysDir = os.path.join(moduleDir, "messages", "Enigmail")
        with open(os.path.join(keysDir, "correspondent_public_key.asc"), "r") as correspondentKeyFile:
            correspondentKey = correspondentKeyFile.read()
        with open(os.path.join(keysDir, "correspondent_alt_public_key.asc"), "r") as correspondentKeyFile:
            correspondentKeyAlt = correspondentKeyFile.read()
            
        with email_sec_cache.Pgp("gbr@voidland.org") as pgp:
            pgp.loadCorrespondentKey(correspondentKey)
            self.assertEqual(["44EDCA862A2D87BDB1D9C36B7FB049F79011E1A9"], pgp.correspondentFingerprints)
            pgp.loadCorrespondentKey(correspondentKeyAlt)
            self.assertEqual(["8D73455FF0373B363B719A35C97A6EF5345933AF"], pgp.correspondentFingerprints)


if __name__ == "__main__":
    unittest.main()
