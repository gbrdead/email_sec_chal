# -*- coding: utf-8 -*-
import test.email_sec_cache
import email_sec_cache
import time



class MockDb(email_sec_cache.Db):
    
    timestamp = -1
    
    def getCurrentTimestamp(self):
        return self.timestamp



class DbTests(test.email_sec_cache.Tests):
    
    correspondentEmailAddress = "gbr@voidland.org"
    
    def testRedHerring(self):
        db = MockDb()
        db.timestamp = int(time.time())
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        db.redHerringSent(DbTests.correspondentEmailAddress)
        self.assertTrue(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        db.timestamp += (24*60*60 - 1)
        self.assertTrue(db.isRedHerringSent(DbTests.correspondentEmailAddress))
        db.timestamp += 1
        self.assertFalse(db.isRedHerringSent(DbTests.correspondentEmailAddress))
