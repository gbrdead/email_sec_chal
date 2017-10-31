# -*- coding: utf-8 -*-
import test.email_sec_chal
import email_sec_chal
import logging
import os.path



class ConfigurationTests(test.email_sec_chal.Tests):
    
    def test(self):
        email_sec_chal.configFile = os.path.join(email_sec_chal.resourceDir, "email_sec_chal.ini")
        email_sec_chal.resourceDir = None
        email_sec_chal.dataDir = None
        email_sec_chal.tempDir = None
        email_sec_chal.triggerWords = set()
        email_sec_chal.logLevel = logging.NOTSET
        email_sec_chal.keyUploadServerPort = -1
        email_sec_chal.smtpServerHost = None
        email_sec_chal.silentPeriodSec = -1
        
        email_sec_chal.loadConfiguration()
        
        self.assertEqual("/data/email_sec_chal/res", email_sec_chal.resourceDir)
        self.assertEqual("/data/email_sec_chal", email_sec_chal.dataDir)
        self.assertEqual("/tmp/email_sec_chal", email_sec_chal.tempDir)
        self.assertEqual(set(["GC65Z29", "OC13031"]), email_sec_chal.triggerWords)
        self.assertEqual(logging.INFO, email_sec_chal.logLevel)
        self.assertEqual(8088, email_sec_chal.keyUploadServerPort)
        self.assertEqual("localhost", email_sec_chal.smtpServerHost)
        self.assertEqual(300, email_sec_chal.silentPeriodSec)
