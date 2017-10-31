# -*- coding: utf-8 -*-
import test.email_sec_chal
import email_sec_chal
import unittest.mock
import mailbox
import os.path
import email
import time



def getOnlyElement(collection):
    return next(iter(collection))



class MockMailboxException(Exception):
    pass



class MockMailbox(mailbox.Mailbox):
    
    testMessagesKeysGroups = None
    testMessages = None
    
    locked = False
    lockingCorrect = True
    runs = 0
    pauseBetweenGroupsInSec = -1;
    

    def __init__(self, testMessagesGroups, pauseBetweenGroupsInSec_=0):
        mailbox.Mailbox.__init__(self, email_sec_chal.tempDir)
        self.initTestMessages(testMessagesGroups)
        self.runs = len(testMessagesGroups)
        self.pauseBetweenGroupsInSec = pauseBetweenGroupsInSec_
        
    def initTestMessages(self, testMessagesGroups):
        self.testMessagesKeysGroups = []
        self.testMessages = {}
        msgKey = 0
        for testMessagesGroup in testMessagesGroups:
            testMessagesKeysGroup = []    
            for testMessage in testMessagesGroup:
                self.testMessages[msgKey] = testMessage
                testMessagesKeysGroup.append(msgKey)
                msgKey += 1
            self.testMessagesKeysGroups.append(testMessagesKeysGroup)            
        
    def iterkeys(self):
        if not self.locked:
            self.lockingCorrect = False
            raise MockMailboxException
        
        return list(self.testMessagesKeysGroups[-self.runs])
    
    def get_message(self, key):
        if not self.locked:
            self.lockingCorrect = False
            raise MockMailboxException
        
        return self.testMessages[key]
    
    def remove(self, key):
        if not self.locked:
            self.lockingCorrect = False
            raise MockMailboxException
        
        del self.testMessages[key]
        self.testMessagesKeysGroups[-self.runs].remove(key)

    def lock(self):
        if self.locked:
            self.lockingCorrect = False
            raise MockMailboxException
        if self.runs == 0:
            raise MockMailboxException
        
        self.locked = True
        if self.runs != len(self.testMessagesKeysGroups):
            time.sleep(self.pauseBetweenGroupsInSec)

    def unlock(self):
        if not self.locked:
            self.lockingCorrect = False
            raise MockMailboxException
        
        self.locked = False
        self.runs -= 1
        
        if self.runs > 0:
            self.testMessagesKeysGroups[-self.runs].extend(self.testMessagesKeysGroups[-(self.runs+1)])



class MockOutgoingMessage:

    incomingMsgId = None
    sent = False
    asImpostor = False
    enteredOK = False
    exitedOK = False

    
    def __init__(self, incomingMsg):
        self.incomingMsgId = incomingMsg.originalMessage["Message-ID"]
        
    def __enter__(self):
        self.enteredOK = not self.exitedOK
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.exitedOK = self.enteredOK
    
    def send(self, asImpostor):
        self.sent = True
        self.asImpostor = asImpostor


class MailBotForTesting(email_sec_chal.MailBot):
    
    mockReplies = None
    mockMbox = None
    
    def __init__(self, incomingMessagesGroups, pauseBetweenGroupsInSec=0):
        self.mockReplies = []
        self.mockMbox = MockMailbox(incomingMessagesGroups, pauseBetweenGroupsInSec)
        self.getMailbox = unittest.mock.MagicMock(return_value=self.mockMbox)
    
    def createReplyMessage(self, incomingMsg):
        reply = MockOutgoingMessage(incomingMsg)
        self.mockReplies.append(reply)
        return reply       



class MailBotTests(test.email_sec_chal.Tests):
    
    correspondentEmailAddress = "gbr@voidland.org" 
    correspondentKeyId = "9011E1A9"
    
    messagesDir = None

    
    @classmethod
    def setUpClass(cls):
        test.email_sec_chal.Tests.setUpClass()
        
        moduleDir = os.path.dirname(os.path.abspath(__file__))
        MailBotTests.messagesDir = os.path.join(moduleDir, "messages")
        
        email_sec_chal.triggerWords = set(["GC65Z29", "OC13031"])
        
    @classmethod
    def tearDownClass(cls):
        test.email_sec_chal.Tests.tearDownClass()
        
    def setUp(self):
        test.email_sec_chal.Tests.setUp(self)
        
        test.email_sec_chal.Tests.clearDb()
        
        correspondentPublicKey = test.email_sec_chal.Tests.readPublicKey(MailBotTests.correspondentEmailAddress, MailBotTests.correspondentKeyId)        
        email_sec_chal.Pgp.storeCorrespondentKey(correspondentPublicKey)
        
        email_sec_chal.silentPeriodSec = 0

    def tearDown(self):
        test.email_sec_chal.Tests.tearDown(self)
        
    def readMessage(self, msgFileName):
        msgFilePath = os.path.join(MailBotTests.messagesDir, msgFileName + ".eml")
        with open(msgFilePath, "rb") as f:
            return email.message_from_binary_file(f)
        
    def runMailBot(self, mailBot):
        try:
            mailBot.run()
            self.fail("MailBot exited unexpectedly")
        except MockMailboxException:
            pass
         
        self.assertTrue(mailBot.mockMbox.lockingCorrect)
        
    def assertOutgoingMessage(self, mockOutgoingMsg, incomingMsgId, asImpostor):
        self.assertTrue(mockOutgoingMsg.enteredOK)
        self.assertTrue(mockOutgoingMsg.exitedOK)
        self.assertTrue(mockOutgoingMsg.sent)
        self.assertEqual(incomingMsgId, mockOutgoingMsg.incomingMsgId)
        self.assertEqual(asImpostor, mockOutgoingMsg.asImpostor)

    def assertHappyPath(self, msgFileName):
        validRequestMsg = self.readMessage(msgFileName)
        validRequestMsgId = validRequestMsg["Message-ID"]
         
        mailBot = MailBotForTesting([[validRequestMsg, validRequestMsg, validRequestMsg]])
        self.runMailBot(mailBot)

        self.assertEqual(0, len(mailBot.mockMbox.testMessages))
        self.assertEqual(3, len(mailBot.mockReplies))
        self.assertOutgoingMessage(mailBot.mockReplies[0], validRequestMsgId, True)
        self.assertOutgoingMessage(mailBot.mockReplies[1], validRequestMsgId, False)
        self.assertOutgoingMessage(mailBot.mockReplies[2], validRequestMsgId, False)
        self.assertEqual(0, len(mailBot.failedMessagesKeys))
        
    def testHappyPath(self):
        self.assertHappyPath("validRequestForOfficialBot")
 
    def testHappyPathNonLowercaseSenderAddress(self):
        self.assertHappyPath("validRequestForOfficialBot_non_lowercase_sender_address")
 
    def testMessageCausingException(self):
        validRequestMsg = self.readMessage("validRequestForOfficialBot")
        validRequestMsgId = validRequestMsg["Message-ID"]
         
        mailBot = MailBotForTesting([[validRequestMsg], []])
        mailBot.createReplyMessage = unittest.mock.MagicMock(side_effect=Exception())
        self.runMailBot(mailBot)
         
        msgInMockMbox = getOnlyElement(mailBot.mockMbox.testMessages.values())
        msgInMockMboxId = msgInMockMbox["Message-ID"]
        failedMsg = mailBot.mockMbox.testMessages[getOnlyElement(mailBot.failedMessagesKeys)]
        failedMsgId = failedMsg["Message-ID"]
 
        self.assertEqual(1, len(mailBot.mockMbox.testMessages))
        self.assertEqual(validRequestMsgId, msgInMockMboxId)
        self.assertEqual(0, len(mailBot.mockReplies))
        self.assertEqual(1, len(mailBot.failedMessagesKeys))
        self.assertEqual(validRequestMsgId, failedMsgId)
        self.assertEqual(1, mailBot.createReplyMessage.call_count)
 
    def testEncryptedForImpostor(self):
        validRequestForOfficialBotMsg = self.readMessage("validRequestForOfficialBot")
        validRequestForOfficialBotMsgId = validRequestForOfficialBotMsg["Message-ID"]
        validRequestForImpostorBotMsg = self.readMessage("validRequestForImpostorBot")
        validRequestForImpostorBotMsgId = validRequestForImpostorBotMsg["Message-ID"]
         
        mailBot = MailBotForTesting([[validRequestForOfficialBotMsg, validRequestForOfficialBotMsg, validRequestForImpostorBotMsg]])
        self.runMailBot(mailBot)
 
        self.assertEqual(0, len(mailBot.mockMbox.testMessages))
        self.assertEqual(3, len(mailBot.mockReplies))
        self.assertOutgoingMessage(mailBot.mockReplies[0], validRequestForOfficialBotMsgId, True)
        self.assertOutgoingMessage(mailBot.mockReplies[1], validRequestForOfficialBotMsgId, False)
        self.assertOutgoingMessage(mailBot.mockReplies[2], validRequestForImpostorBotMsgId, True)
        self.assertEqual(0, len(mailBot.failedMessagesKeys))
 
    def testInvalidRequests(self):
        messages = []
         
        invalidRequestsDir = os.path.join(MailBotTests.messagesDir, "Enigmail")
        for root, _, files in os.walk(invalidRequestsDir):
            for fileName in files:
                fileExt = fileName[-len(".eml"):]
                if fileExt.lower() != ".eml":
                    continue
                msgFilePath = os.path.join(root, fileName)
                 
                with open(msgFilePath, "rb") as f:
                    msg = email.message_from_binary_file(f)
                    messages.append(msg)
        self.assertLess(0, len(messages))
         
        mailBot = MailBotForTesting([messages])
        self.runMailBot(mailBot)
 
        self.assertEqual(0, len(mailBot.mockMbox.testMessages))
        self.assertEqual(0, len(mailBot.mockReplies))
        self.assertEqual(0, len(mailBot.failedMessagesKeys))
 
    def assertHappyPathFromMyself(self, msgFileName):
        validRequestMsg = self.readMessage(msgFileName)
          
        mailBot = MailBotForTesting([[validRequestMsg, validRequestMsg]])
        self.runMailBot(mailBot)
 
        self.assertEqual(0, len(mailBot.mockMbox.testMessages))
        self.assertEqual(0, len(mailBot.mockReplies))
        self.assertEqual(0, len(mailBot.failedMessagesKeys))
         
    def testHappyPathFromOfficialBot(self):
        self.assertHappyPathFromMyself("validRequestFromOfficialBot")
  
    def testHappyPathFromImpostorBot(self):
        self.assertHappyPathFromMyself("validRequestFromImpostorBot")
         
    def assertBrokenMessage(self, msgFileName):
        brokenMsg = self.readMessage(msgFileName)
          
        mailBot = MailBotForTesting([[brokenMsg]])
        self.runMailBot(mailBot)
 
        self.assertEqual(0, len(mailBot.mockMbox.testMessages))
        self.assertEqual(0, len(mailBot.mockReplies))
        self.assertEqual(0, len(mailBot.failedMessagesKeys))
         
    def testMessageWithMissingContentType(self):
        self.assertBrokenMessage("missing_content_type")
 
    def testMessageWithUnparsableContentDisposition(self):
        self.assertBrokenMessage("unparsable_content_disposition")

    def testSilence(self):
        email_sec_chal.silentPeriodSec = 20
        
        validRequestMsg = self.readMessage("validRequestForOfficialBot")
        validRequestMsgId = validRequestMsg["Message-ID"]
         
        mailBot = MailBotForTesting([[validRequestMsg, validRequestMsg], [validRequestMsg], [validRequestMsg, validRequestMsg]], 10)
        self.runMailBot(mailBot)

        self.assertEqual(0, len(mailBot.mockMbox.testMessages))
        self.assertEqual(3, len(mailBot.mockReplies))
        self.assertOutgoingMessage(mailBot.mockReplies[0], validRequestMsgId, True)
        self.assertOutgoingMessage(mailBot.mockReplies[1], validRequestMsgId, False)
        self.assertOutgoingMessage(mailBot.mockReplies[2], validRequestMsgId, False)
        self.assertEqual(0, len(mailBot.failedMessagesKeys))
