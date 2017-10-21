# -*- coding: utf-8 -*-
import test.email_sec_chal
import email_sec_chal



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
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        
        email_sec_chal.Pgp.storeCorrespondentKey(DbTests.correspondentPublicKey)
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        
        db.redHerringSent(DbTests.correspondentEmailAddress)
        self.assertTrue(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        
        email_sec_chal.Pgp.storeCorrespondentKey(DbTests.correspondentPublicKey)
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
