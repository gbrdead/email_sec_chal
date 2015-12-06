import mailbox
import time
import email_sec_cache
import logging


configDir = u"/data/email_sec_cache"
dataDir = u"/data/email_sec_cache"
tempDir = u"/tmp/email_sec_cache"
geocacheName = u"GC65Z29"
logLevel = logging.INFO


class EmailSecCacheException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class MailBot:
    
    mbox = None

    
    def __init__(self):
        self.mbox = mailbox.Maildir(u"~/Maildir", factory = mailbox.MaildirMessage)
    
    def run(self):
        logging.info(u"Mailbot started")
        
        while True:
            time.sleep(1)
            
            self.mbox.lock()
            try:
                while self.mbox:
                    _, origMsg = self.mbox.popitem()
                    
                    try:
                        from_ = email_sec_cache.getHeaderAsUnicode(origMsg, "From")
                        msgId = email_sec_cache.getHeaderAsUnicode(origMsg, "Message-ID")
                        incomingMsg = email_sec_cache.IncomingMessage(origMsg)
                        
                        words = email_sec_cache.extractWords(incomingMsg.getMessageTexts())
                        if unicode.upper(email_sec_cache.geocacheName) in map(unicode.upper, words):
                            logging.info(u"Received valid request from %s (%s)" % (from_, msgId))
                            spam = False
                        else:
                            spam = True
                            logging.warning(u"Received invalid request (spam) from %s (%s)" % (from_, msgId))
                        
                        goshkoMayReply = incomingMsg.isEncrypted or not spam
                        mariykaMayReply = incomingMsg.isEncrypted and incomingMsg.isVerified and not spam

                        if goshkoMayReply:
                            logging.info(u"Goshko may reply to %s (%s)" % (from_, msgId))
                        if mariykaMayReply:
                            logging.info(u"Mariyka may reply to %s (%s)" % (from_, msgId))
                        
                        outgoingMsg = email_sec_cache.OutgoingMessage(incomingMsg)    
                        
                        
                    except Exception:
                        logging.exception(u"Failed processing message %s" % msgId)

            finally:            
                self.mbox.unlock()


if __name__ == "__main__":
    
    logging.basicConfig(format=u"%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=logLevel)

    try:
        mailBot = MailBot()
        mailBot.run()
    except:
        logging.exception(u"Mailbot stopped with an exception")
