import mailbox
import time
import email_sec_cache


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
        while True:
            time.sleep(1)
            self.mbox.lock()
            
            while self.mbox:
                _, origMsg = self.mbox.popitem()
                
                try:
                    msg = email_sec_cache.Message(origMsg)
                    print str(msg.isEncrypted) + " " + str(msg.isVerified)
                    texts = msg.getMessageTexts()
                    for text in texts:
                        print text + "\n"
                except email_sec_cache.EmailSecCacheException as e:
                    print e
                    print origMsg
            
            self.mbox.unlock()


if __name__ == "__main__":
    mailBot = MailBot()
    mailBot.run()
