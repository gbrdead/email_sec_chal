# -*- coding: utf-8 -*-
import test.email_sec_cache
import email_sec_cache



class DbTests(test.email_sec_cache.Tests):
    
    correspondentEmailAddress = "gbr@voidland.org"
    correspondentKeyId = "9011E1A9"
    correspondentPublicKey = None
    
    
    @classmethod
    def setUpClass(cls):
        test.email_sec_cache.Tests.setUpClass()
        
        DbTests.correspondentPublicKey = test.email_sec_cache.Tests.readPublicKey(DbTests.correspondentEmailAddress, DbTests.correspondentKeyId)        
        
    @classmethod
    def tearDownClass(cls):
        test.email_sec_cache.Tests.tearDownClass()
    
    def setUp(self):
        test.email_sec_cache.Tests.setUp(self)
        
        test.email_sec_cache.Tests.clearDb()

    def tearDown(self):
        test.email_sec_cache.Tests.tearDown(self)

    
    def testRedHerring(self):
        db = email_sec_cache.Db()
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        
        email_sec_cache.Pgp.storeCorrespondentKey(DbTests.correspondentPublicKey)
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        
        db.redHerringSent(DbTests.correspondentEmailAddress)
        self.assertTrue(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        
        email_sec_cache.Pgp.storeCorrespondentKey(DbTests.correspondentPublicKey)
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
