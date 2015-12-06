import mailbox
import time
import email_sec_cache
import logging


configDir = "/data/email_sec_cache"
dataDir = "/data/email_sec_cache"
tempDir = "/tmp/email_sec_cache"
geocacheName = "GC65Z29"
logLevel = logging.INFO


class EmailSecCacheException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class MailBot:
    
    mbox = None

    
    def __init__(self):
        self.mbox = mailbox.Maildir("~/Maildir", factory = mailbox.MaildirMessage)
    
    def run(self):
        logging.info("Mailbot started")
        
        while True:
            time.sleep(1)
            
            self.mbox.lock()
            try:
                while self.mbox:
                    _, origMsg = self.mbox.popitem()
                    
                    try:
                        from_ = origMsg["From"]
                        msgId = origMsg["Message-ID"]
                        msg = email_sec_cache.IncomingMessage(origMsg)
                        
                        words = email_sec_cache.extractWords(msg.getMessageTexts())
                        if unicode.upper(email_sec_cache.geocacheName) in map(unicode.upper, words):
                            logging.info("Received valid request from %s (%s)" % (from_, msgId))
                            spam = False
                        else:
                            spam = True
                            logging.warning("Received invalid request (spam) from %s (%s)" % (from_, msgId))
                        
                        goshkoMayReply = msg.isEncrypted or not spam
                        mariykaMayReply = msg.isEncrypted and msg.isVerified and not spam

                        if goshkoMayReply:
                            logging.info("Goshko may reply to %s (%s)" % (from_, msgId))
                        if mariykaMayReply:
                            logging.info("Mariyka may reply to %s (%s)" % (from_, msgId))
                            
                        
                        
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
