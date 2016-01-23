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
        
    def send(self, asImpostor):
        if asImpostor:
            filePrefix = "impostor"
        else:
            filePrefix = "official"
        
        htmlResponsePath = os.path.join(email_sec_cache.configDir, filePrefix + ".html")
        with open(htmlResponsePath, "r") as htmlResponseFile:
            htmlResponse = htmlResponseFile.read()
            
        h = html2text.HTML2Text()
        h.ignore_links = True
        plainTextResponse = h.handle(htmlResponse)
            
        multipartAlt = email.mime.multipart.MIMEMultipart("alternative")
        multipartAlt.attach(email.mime.text.MIMEText(plainTextResponse, "plain"))            
        multipartAlt.attach(email.mime.text.MIMEText(htmlResponse, "html"))
        
        spoilerPicturePath = os.path.join(email_sec_cache.configDir, filePrefix + "Spoiler.jpg")
        with open(spoilerPicturePath, "rb") as spoilerPictureFile:
            spoilerPicture = spoilerPictureFile.read()
        spoilerPictureAttachment = email.mime.image.MIMEImage(spoilerPicture)
        spoilerPictureAttachment.add_header("Content-Disposition", "attachment", filename="spoiler.jpg")
        
        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg.attach(multipartAlt)
        msg.attach(spoilerPictureAttachment)
        
        msg = self.pgp.signAndEncrypt(msg, asImpostor)
        
        msg["To"] = self.incomingMsg.originalMessage["From"]
        msg["From"] = email_sec_cache.Pgp.botFrom
        msg["Subject"] = getReSubject(self.incomingMsg.originalMessage)
        
        smtpConn = smtplib.SMTP('localhost')
        smtpConn.sendmail(email_sec_cache.Pgp.botFrom, self.incomingMsg.emailAddress, msg.as_string())
        smtpConn.quit()
