# -*- coding: utf-8 -*-
import email_sec_cache 
import email.mime.text
import smtplib
import email.mime.multipart
import logging
import os.path
import email.mime.image
import html2text



def getReSubject(msg):
    subject = msg["Subject"]
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
    incomingMsg = None
    
    def __init__(self, incomingMsg_):
        self.incomingMsg = incomingMsg_
        self.pgp = email_sec_cache.Pgp(self.incomingMsg.emailAddress )
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        self.pgp.close()
        logging.debug("EmailSecCache: Closed outgoing message to %s" % self.incomingMsg.emailAddress )
        
        
    def sendAsOfficialBot(self):
        self.send(self.pgp.officialGpg, "official")
        
    def sendAsImpostorBot(self):
        self.send(self.pgp.impostorGpg, "impostor")

    def send(self, gpg, filePrefix):
        htmlResponsePath = os.path.join(email_sec_cache.configDir, filePrefix + ".html")
        with open(htmlResponsePath, "r") as htmlResponseFile:
            htmlResponse = htmlResponseFile.read()
            
        h = html2text.HTML2Text()
        h.ignore_links = True
        plainTextResponse = h.handle(htmlResponse)
            
        multipartAlt = email.mime.multipart.MIMEMultipart("alternative")
        multipartAlt.attach(email.mime.text.MIMEText(plainTextResponse, "plain"))            
        multipartAlt.attach(email.mime.text.MIMEText(htmlResponse, "html"))
        
        hintPicturePath = os.path.join(email_sec_cache.configDir, filePrefix + "Hint.jpg")
        with open(hintPicturePath, "rb") as hintPictureFile:
            hintPicture = hintPictureFile.read()
        
        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg.attach(multipartAlt)
        msg.attach(email.mime.image.MIMEImage(hintPicture)) # TODO: make an attachment; take care of the file name
        
        msg["To"] = self.incomingMsg.originalMessage["From"]
        msg["From"] = email_sec_cache.Pgp.botFrom
        msg["Subject"] = getReSubject(self.incomingMsg.originalMessage)
        
        encryptedAndSignedMsg = msg #TODO: reimplement correclty gpg.sign_and_encrypt_email(msg, always_trust=True)
        
        smtpConn = smtplib.SMTP('localhost')
        smtpConn.sendmail(email_sec_cache.Pgp.botFrom, self.incomingMsg.emailAddress , encryptedAndSignedMsg.as_string())
        smtpConn.quit()
