# -*- coding: utf-8 -*-
import email_sec_cache 
import email.mime.text
import smtplib



def getReSubject(msg):
    subject = email_sec_cache.getHeaderAsUnicode(msg, "Subject")
    if not subject:
        subject = "Re:"
    else:
        if not subject.lower().startswith("re:"):
            subject = "Re: " + subject
    return subject



class OutgoingMessage:
    
    pgp = None
    msg = None
    correspondentEmailAddress = None
    
    def __init__(self, incomingMsg):
        
        self.correspondentEmailAddress = incomingMsg.emailAddress 
        
        self.pgp = email_sec_cache.Pgp(self.correspondentEmailAddress)
        # TODO: close self.pgp
        
        self.msg = email.mime.text.MIMEText("Alabala Алабала", "plain", "utf-8")
        
        self.msg["To"] = incomingMsg.originalMessage["From"]
        email_sec_cache.setHeaderFromUnicode(self.msg, "From", email_sec_cache.Pgp.botFrom)
        
        subject = getReSubject(incomingMsg.originalMessage)
        email_sec_cache.setHeaderFromUnicode(self.msg, "Subject", subject)
        
    def sendAsOfficialBot(self):
        self.sendAs(self.pgp.officialGpg)
        
    def sendAsImpostorBot(self):
        self.sendAs(self.pgp.impostorGpg)
         
    def sendAs(self, gpg):
        encryptedAndSignedMsg = gpg.sign_and_encrypt_email(self.msg, always_trust=True)
        s = smtplib.SMTP('localhost')
        s.sendmail(email_sec_cache.Pgp.botFrom, self.correspondentEmailAddress, encryptedAndSignedMsg.as_string())
        s.quit()
