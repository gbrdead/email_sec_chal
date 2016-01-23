# -*- coding: utf-8 -*-
import mailbox
import time
import email_sec_cache
import logging
import email.utils


configDir = "/data/email_sec_cache"
officialBotKeysFileName = "officialBot.asc"
impostorBotKeysFileName = "impostorBot.asc"

dataDir = "/data/email_sec_cache"
tempDir = "/tmp/email_sec_cache"

geocacheName = "GC65Z29"
logLevel = logging.INFO



class MailBot:
    
    mbox = None
    db = None
    failedMessagesKeys = None

    
    def __init__(self):
        self.mbox = mailbox.Maildir("~/Maildir", factory = mailbox.MaildirMessage)
        self.db = email_sec_cache.Db()
        self.failedMessagesKeys = set()
    
    def run(self):
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
                            if msgPart is None:
                                continue
                            
                            logging.info("EmailSecCache: Received a valid request from %s (%s)" % (emailAddress, msgId))
                            impostorShouldReply = msgPart.forImpostor or not self.db.isRedHerringSent(emailAddress) 
    
                            with email_sec_cache.OutgoingMessage(incomingMsg) as replyMsg:
                                if impostorShouldReply:
                                    replyMsg.sendAsImpostorBot()
                                    logging.info("EmailSecCache: Replied to %s as the impostor bot (%s)" % (emailAddress, msgId))
                                    self.db.redHerringSent(emailAddress)
                                else:
                                    replyMsg.sendAsOfficialBot()
                                    logging.info("EmailSecCache: Replied to %s as the official bot (%s)" % (emailAddress, msgId))
                                    
                        self.mbox.discard(msgKey)
                        
                    except Exception:
                        logging.exception("Failed processing message %s" % msgKey)
                        self.failedMessagesKeys.add(msgKey)
                        
            finally:            
                self.mbox.unlock()

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


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logLevel)

    try:
        mailBot = MailBot()
        mailBot.run()
    except:
        logging.exception("Mailbot stopped with an exception")
