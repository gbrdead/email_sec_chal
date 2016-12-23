# -*- coding: utf-8 -*-
import test.email_sec_cache
import email_sec_cache



class PgpTests(test.email_sec_cache.Tests):
    
    correspondentEmailAddress = "gbr@voidland.org" 
    correspondentKeyId = "9011E1A9"
    correspondentKeyAltId = "345933AF"
    
        
    def testStoreNewCorrespondentKey(self):
        correspondentKey = test.email_sec_cache.Tests.readPublicKey(PgpTests.correspondentEmailAddress, PgpTests.correspondentKeyId)
        correspondentKeyAlt = test.email_sec_cache.Tests.readPublicKey(PgpTests.correspondentEmailAddress, PgpTests.correspondentKeyAltId)
        
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

    def testStoreCorrespondentKeyWithStrangeRealNameInUid(self):
        correspondentKey = test.email_sec_cache.Tests.readPublicKey("dimpata@gmail.com", "0556B1B2")
        
        email_sec_cache.Pgp.storeCorrespondentKey(correspondentKey)
        with email_sec_cache.Pgp("dimpata@gmail.com") as pgp:
            self.assertEqual(["95E12FD2351D3CC7EFBAE77B514D3A510556B1B2"], pgp.correspondentFingerprints)
