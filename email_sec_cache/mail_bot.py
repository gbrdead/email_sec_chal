# -*- coding: utf-8 -*-
import mailbox
import time
import email_sec_cache
import logging
import email.utils



class MailBot:
    
    mbox = None
    db = None
    failedMessagesKeys = None

    
    def getMailbox(self):
        return mailbox.Maildir("~/Maildir", factory = mailbox.MaildirMessage)
    
    def run(self):
        self.mbox = self.getMailbox()
        self.db = email_sec_cache.Db()
        self.failedMessagesKeys = set()

        logging.info("EmailSecCache: Mailbot started")
        
        while True:
            time.sleep(1)
            
            self.mbox.lock()
            try:
                for msgKey in self.mbox.iterkeys():
                    if msgKey in self.failedMessagesKeys:
                        logging.debug("EmailSecCache: Skipping previously failed message with key %s" % msgKey)
                        continue
                    
                    try:
                        origMsg = self.mbox[msgKey]
                        from_ = origMsg["From"]
                        _, emailAddress = email.utils.parseaddr(from_)
                        msgId = origMsg["Message-ID"]
                        
                        with email_sec_cache.IncomingMessage.create(origMsg) as incomingMsg:
                            msgPart = self.findValidMessagePart(incomingMsg, emailAddress, msgId)
                            if msgPart is not None:
                                logging.info("EmailSecCache: Received a valid request from %s (%s)" % (emailAddress, msgId))
                                impostorShouldReply = msgPart.forImpostor or not self.db.isRedHerringSent(emailAddress)
                                self.reply(impostorShouldReply, incomingMsg, emailAddress, msgId)
                                    
                        self.mbox.discard(msgKey)
                        
                    except Exception:
                        logging.exception("Failed processing message %s" % msgKey)
                        self.failedMessagesKeys.add(msgKey)
                        
            finally:            
                self.mbox.unlock()
                
    def reply(self, asImpostor, incomingMsg, emailAddress, msgId):
        with self.createReplyMessage(incomingMsg) as replyMsg:
            replyMsg.send(asImpostor)
            if asImpostor:
                logging.info("EmailSecCache: Replied to %s as the impostor bot (%s)" % (emailAddress, msgId))
                self.db.redHerringSent(emailAddress)
            else:
                logging.info("EmailSecCache: Replied to %s as the official bot (%s)" % (emailAddress, msgId))
                
    def createReplyMessage(self, incomingMsg):
        return email_sec_cache.OutgoingMessage(incomingMsg)
                
    def findValidMessagePart(self, incomingMsg, emailAddress, msgId):
        for msgPart in incomingMsg.getMessageParts():
            if not msgPart.encrypted:
                logging.warning("EmailSecCache: Ignoring unencrypted message part in incoming message from %s (%s)" % (emailAddress, msgId))
                continue
            if not msgPart.signedAndVerified:
                logging.warning("EmailSecCache: Ignoring unverified message part in incoming message from %s (%s)" % (emailAddress, msgId))
                continue
            words = email_sec_cache.extractWords(msgPart.getPlainText())
            if not str.upper(email_sec_cache.geocacheName) in list(map(str.upper, words)):
                logging.warning("EmailSecCache: Ignoring invalid message part in incoming message from %s (%s)" % (emailAddress, msgId))
                continue
            return msgPart
        return None


