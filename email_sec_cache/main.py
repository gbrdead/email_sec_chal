# -*- coding: utf-8 -*-
import mailbox
import time
import email_sec_cache
import logging
import email


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

    
    def __init__(self):
        self.mbox = mailbox.Maildir("~/Maildir", factory = mailbox.MaildirMessage)
        self.db = email_sec_cache.Db()
    
    def run(self):
        logging.info("EmailSecCache: Mailbot started")
        
        while True:
            time.sleep(1)
            
            self.mbox.lock()
            try:
                while self.mbox:
                    _, origMsg = self.mbox.popitem()
                    
                    try:
                        from_ = email_sec_cache.getHeaderAsUnicode(origMsg, "From")
                        _, emailAddress = email.utils.parseaddr(from_)
                        msgId = email_sec_cache.getHeaderAsUnicode(origMsg, "Message-ID")
                        incomingMsg = email_sec_cache.IncomingMessage(origMsg)

                        ignore = False                        
                        if not incomingMsg.isEncrypted:
                            logging.warning("EmailSecCache: Ignoring invalid request (unencrypted) from %s (%s)" % (emailAddress, msgId))
                            ignore = True
                        if not incomingMsg.isVerified:
                            logging.warning("EmailSecCache: Ignoring invalid request (unverified) from %s (%s)" % (emailAddress, msgId))
                            ignore = True
                        words = email_sec_cache.extractWords(incomingMsg.getMessageTexts())
                        if not str.upper(email_sec_cache.geocacheName) in list(map(str.upper, words)):
                            logging.warning("EmailSecCache: Ignoring invalid request (spam) from %s (%s)" % (emailAddress, msgId))
                            ignore = True
                        if ignore:
                            continue
                        
                        logging.info("EmailSecCache: Received a valid request from %s (%s)" % (emailAddress, msgId))
                        impostorShouldReply = incomingMsg.isForImpostor or not self.db.isRedHerringSent(emailAddress) 

                        replyMsg = email_sec_cache.OutgoingMessage(incomingMsg)
                        if impostorShouldReply:
                            logging.info("EmailSecCache: Replying to %s as the impostor bot (%s)" % (emailAddress, msgId))
                            replyMsg.sendAsImpostorBot()
                            self.db.redHerringSent(emailAddress)
                        else:
                            logging.info("EmailSecCache: Replying to %s as the official bot (%s)" % (emailAddress, msgId))
                            replyMsg.sendAsOfficialBot()
                            
                        
                    except Exception:
                        logging.exception("Failed processing message %s" % msgId)

            finally:            
                self.mbox.unlock()


if __name__ == "__main__":
    
    logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logLevel)

    try:
        mailBot = MailBot()
        mailBot.run()
    except:
        logging.exception("Mailbot stopped with an exception")
