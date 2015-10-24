import mailbox
import time
import email_sec_cache


class MailBot:
    
    mbox = None

    
    def __init__(self):
        self.mbox = mailbox.Maildir("~/Maildir", factory=mailbox.MaildirMessage)
    
    def run(self):
        while True:
            time.sleep(1)
            self.mbox.lock()
            
            while self.mbox:
                _, msg = self.mbox.popitem()
                
                try:
                    isEncrypted, isVerified, plainMsg = self.pgp.processMessage(msg)
                    print str(isEncrypted) + " " + str(isVerified)
                except email_sec_cache.PgpException as e:
                    print e
            
            self.mbox.unlock()


if __name__ == "__main__":
    print "Mail bot starting..."
    # Temporary: populate DB
    pgp = email_sec_cache.Pgp("gbr@voidland.org")
    pgp.loadCorrespondentKeyFromServer("9011E1A9")
    
    mailBot = MailBot()
    mailBot.run()
