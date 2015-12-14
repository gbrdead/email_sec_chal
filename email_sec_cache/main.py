# -*- coding: utf-8 -*-
import mailbox
import time
import email_sec_cache
import logging
import email


configDir = u"/data/email_sec_cache"
officialBotKeysFileName = u"officialBot.asc"
impostorBotKeysFileName = u"impostorBot.asc"

dataDir = u"/data/email_sec_cache"
tempDir = u"/tmp/email_sec_cache"

geocacheName = u"GC65Z29"
logLevel = logging.DEBUG


class EmailSecCacheException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class MailBot:
    
    mbox = None
    db = None

    
    def __init__(self):
        self.mbox = mailbox.Maildir(u"~/Maildir", factory = mailbox.MaildirMessage)
        self.db = email_sec_cache.Db()
    
    def run(self):
        logging.info(u"EmailSecCache: Mailbot started")
        
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
                            logging.warning(u"EmailSecCache: Ignoring invalid request (unencrypted) from %s (%s)" % (emailAddress, msgId))
                            ignore = True
                        if not incomingMsg.isVerified:
                            logging.warning(u"EmailSecCache: Ignoring invalid request (unverified) from %s (%s)" % (emailAddress, msgId))
                            ignore = True
                        words = email_sec_cache.extractWords(incomingMsg.getMessageTexts())
                        if not unicode.upper(email_sec_cache.geocacheName) in map(unicode.upper, words):
                            logging.warning(u"EmailSecCache: Ignoring invalid request (spam) from %s (%s)" % (emailAddress, msgId))
                            ignore = True
                        if ignore:
                            continue
                        
                        logging.info(u"EmailSecCache: Received a valid request from %s (%s)" % (emailAddress, msgId))
                        impostorShouldReply = incomingMsg.isForImpostor or not self.db.isRedHerringSent(emailAddress) 

                        replyMsg = email_sec_cache.OutgoingMessage(incomingMsg)
                        if impostorShouldReply:
                            logging.info(u"EmailSecCache: Replying to %s as the impostor bot (%s)" % (emailAddress, msgId))
                            replyMsg.sendAsImpostorBot()
                            self.db.redHerringSent(emailAddress)
                        else:
                            logging.info(u"EmailSecCache: Replying to %s as the official bot (%s)" % (emailAddress, msgId))
                            replyMsg.sendAsOfficialBot()
                            
                        
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
