# -*- coding: utf-8 -*-
import test.email_sec_chal
import email_sec_chal
import time



class DbTests(test.email_sec_chal.Tests):
    
    correspondentEmailAddress = "gbr@voidland.org"
    correspondentKeyId = "9011E1A9"
    correspondentPublicKey = None
    
    
    @classmethod
    def setUpClass(cls):
        test.email_sec_chal.Tests.setUpClass()
        
        DbTests.correspondentPublicKey = test.email_sec_chal.Tests.readPublicKey(DbTests.correspondentEmailAddress, DbTests.correspondentKeyId)        
        
    @classmethod
    def tearDownClass(cls):
        test.email_sec_chal.Tests.tearDownClass()
    
    def setUp(self):
        test.email_sec_chal.Tests.setUp(self)
        
        test.email_sec_chal.Tests.clearDb()

    def tearDown(self):
        test.email_sec_chal.Tests.tearDown(self)

    
    def testRedHerring(self):
        db = email_sec_chal.Db()
        self.assertFalse(db.getRedHerringSentTimestamp(DbTests.correspondentEmailAddress) >= 0)
        
        email_sec_chal.Pgp.storeCorrespondentKey(DbTests.correspondentPublicKey)
        self.assertFalse(db.getRedHerringSentTimestamp(DbTests.correspondentEmailAddress) >= 0)
        
        db.redHerringSent(DbTests.correspondentEmailAddress)
        self.assertTrue(db.getRedHerringSentTimestamp(DbTests.correspondentEmailAddress) >= 0)
        
        email_sec_chal.Pgp.storeCorrespondentKey(DbTests.correspondentPublicKey)
        self.assertFalse(db.getRedHerringSentTimestamp(DbTests.correspondentEmailAddress) >= 0)
        
    def testRedHerringShouldNotResetSilentPeriod(self):
        db = email_sec_chal.Db()
        email_sec_chal.Pgp.storeCorrespondentKey(DbTests.correspondentPublicKey)
        
        db.redHerringSent(DbTests.correspondentEmailAddress)
        redHerringSentTimestamp1 = db.getRedHerringSentTimestamp(DbTests.correspondentEmailAddress)
        self.assertTrue(redHerringSentTimestamp1 >= 0)
        
        while db.getCurrentTimestamp() <= redHerringSentTimestamp1:
            time.sleep(1)    
        
        db.redHerringSent(DbTests.correspondentEmailAddress)
        redHerringSentTimestamp2 = db.getRedHerringSentTimestamp(DbTests.correspondentEmailAddress)
        self.assertEqual(redHerringSentTimestamp1, redHerringSentTimestamp2)
