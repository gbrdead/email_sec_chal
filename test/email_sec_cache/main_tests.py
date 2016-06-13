# -*- coding: utf-8 -*-
import test.email_sec_cache
import email_sec_cache
import logging
import os.path



class ConfigurationTests(test.email_sec_cache.Tests):
    
    def test(self):
        email_sec_cache.configFile = os.path.join(email_sec_cache.resourceDir, "email_sec_cache.ini")
        email_sec_cache.resourceDir = None
        email_sec_cache.dataDir = None
        email_sec_cache.tempDir = None
        email_sec_cache.geocacheNames = set()
        email_sec_cache.logLevel = logging.NOTSET
        email_sec_cache.keyUploadServerPort = -1
        email_sec_cache.smtpServerHost = None
        
        email_sec_cache.loadConfiguration()
        
        self.assertEqual("/data/email_sec_cache/res", email_sec_cache.resourceDir)
        self.assertEqual("/data/email_sec_cache", email_sec_cache.dataDir)
        self.assertEqual("/tmp/email_sec_cache", email_sec_cache.tempDir)
        self.assertEqual(set(["GC65Z29", "OC13031"]), email_sec_cache.geocacheNames)
        self.assertEqual(logging.INFO, email_sec_cache.logLevel)
        self.assertEqual(8088, email_sec_cache.keyUploadServerPort)
        self.assertEqual("localhost", email_sec_cache.smtpServerHost)
