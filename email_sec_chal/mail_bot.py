# -*- coding: utf-8 -*-
import mailbox
import time
import email_sec_chal
import logging



class MailBot:
    
    mbox = None
    db = None
    failedMessagesKeys = None

    
    def getMailbox(self):
        return mailbox.Maildir("~/Maildir", factory = mailbox.MaildirMessage)
    
    def run(self):
        self.mbox = self.getMailbox()
        self.db = email_sec_chal.Db()
        self.failedMessagesKeys = set()

        logging.info("EmailSecChal: mail_bot: Successfully started")
        
        while True:
            time.sleep(1)
            
            self.mbox.lock()
            try:
                for msgKey in self.mbox.iterkeys():
                    if msgKey in self.failedMessagesKeys:
                        logging.debug("EmailSecChal: mail_bot: Skipping previously failed message with key %s" % msgKey)
                        continue
                    origMsg = self.mbox[msgKey]
                    
                    try:
                        with email_sec_chal.IncomingMessage.create(origMsg) as incomingMsg:
                        
                            if incomingMsg.emailAddress == email_sec_chal.Pgp.botEmailAddress:
                                logging.warning("EmailSecChal: mail_bot: Ignoring spoofed message from myself (%s)" % incomingMsg.id)
                            else:
                                msgRecipientsEmailAddresses = email_sec_chal.util.getMessageRecipientsEmailAddresses(origMsg)
                                if email_sec_chal.Pgp.botEmailAddress in msgRecipientsEmailAddresses:
                                    self.processRequestMessage(incomingMsg)
                                
                    except Exception:
                        logging.exception("EmailSecChal: mail_bot: Failed processing message %s" % msgKey)
                        self.failedMessagesKeys.add(msgKey)
                        
                    if msgKey not in self.failedMessagesKeys:    
                        self.mbox.discard(msgKey)
                        
            finally:            
                self.mbox.unlock()
                
    def processRequestMessage(self, incomingMsg):
        redHerringSentTimestamp = self.db.getRedHerringSentTimestamp(incomingMsg.emailAddress)
        if redHerringSentTimestamp >= 0:
            endOfSilentPeriodTimestamp = redHerringSentTimestamp + email_sec_chal.silentPeriodSec
            if self.db.getCurrentTimestamp() < endOfSilentPeriodTimestamp:
                logging.info("EmailSecChal: mail_bot: Ignoring a request from %s (%s) in the silent period" % (incomingMsg.emailAddress, incomingMsg.id))
                return
        
        msgPart = self.findValidMessagePart(incomingMsg, incomingMsg.emailAddress, incomingMsg.id)
        if msgPart is not None:
            logging.info("EmailSecChal: mail_bot: Received a valid request from %s (%s)" % (incomingMsg.emailAddress, incomingMsg.id))
            impostorShouldReply = msgPart.forImpostor or redHerringSentTimestamp < 0
            self.reply(impostorShouldReply, incomingMsg, incomingMsg.emailAddress, incomingMsg.id)
        
    def reply(self, asImpostor, incomingMsg, emailAddress, msgId):
        with self.createReplyMessage(incomingMsg) as replyMsg:
            replyMsg.send(asImpostor)
            if asImpostor:
                logging.info("EmailSecChal: mail_bot: Replied to %s as the impostor bot (%s)" % (emailAddress, msgId))
                self.db.redHerringSent(emailAddress)
            else:
                logging.info("EmailSecChal: mail_bot: Replied to %s as the official bot (%s)" % (emailAddress, msgId))
                
    def createReplyMessage(self, incomingMsg):
        return email_sec_chal.OutgoingMessage(incomingMsg)
                
    def findValidMessagePart(self, incomingMsg, emailAddress, msgId):
        for msgPart in incomingMsg.getMessageParts():
            if not msgPart.encrypted:
                logging.warning("EmailSecChal: mail_bot: Ignoring unencrypted message part in incoming message from %s (%s)" % (emailAddress, msgId))
                continue
            if not msgPart.signedAndVerified:
                logging.warning("EmailSecChal: mail_bot: Ignoring unverified message part in incoming message from %s (%s)" % (emailAddress, msgId))
                continue
            words = email_sec_chal.extractWords(msgPart.getPlainText())
            if not email_sec_chal.triggerWords & set(map(str.upper, words)):
                logging.warning("EmailSecChal: mail_bot: Ignoring invalid message part in incoming message from %s (%s)" % (emailAddress, msgId))
                continue
            return msgPart
        return None
