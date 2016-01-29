# -*- coding: utf-8 -*-
import email_sec_cache 
import email.mime.text
import smtplib
import email.mime.multipart
import logging
import os.path
import email.mime.image
import html2text
import email.mime.application
import email.encoders



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
        msg = self.construct(asImpostor)
        msg = self.pgp.signAndEncrypt(msg, asImpostor)
        
        msg["To"] = self.incomingMsg.originalMessage["From"]
        msg["From"] = email_sec_cache.Pgp.botFrom
        msg["Subject"] = getReSubject(self.incomingMsg.originalMessage)
        
        smtpConn = smtplib.SMTP('localhost')
        smtpConn.sendmail(email_sec_cache.Pgp.botFrom, self.incomingMsg.emailAddress, msg.as_string())
        smtpConn.quit()
        
    def construct(self, asImpostor):
        if asImpostor:
            filePrefix = "impostor"
        else:
            filePrefix = "official"
            
        msg = email.mime.multipart.MIMEMultipart("mixed")
        email_sec_cache.removeMimeVersion(msg)
        
        text = self.constructTextMessagePart(filePrefix)
        msg.attach(text)
        
        spoilerPictureAttachment = self.constructSpoilerMessagePart(filePrefix)
        msg.attach(spoilerPictureAttachment)
        
        if asImpostor:
            impostorPublicKey = self.pgp.getImpostorPublicKey()
            impostorPublicKeyAttachment = email.mime.application.MIMEApplication(impostorPublicKey, "pgp-keys", email.encoders.encode_quopri)
            email_sec_cache.removeMimeVersion(impostorPublicKeyAttachment)
            email_sec_cache.setMimeAttachmentFileName(impostorPublicKeyAttachment, "public_key.asc")
            msg.attach(impostorPublicKeyAttachment)

            # A workaround for a bug in Enigmail 1.8.2 (fixed in 1.9):
            msg.as_string()
            boundary = msg.get_boundary()
            boundary = "--" + boundary[2:]
            msg.set_boundary(boundary)
            
        return msg

    def constructTextMessagePart(self, filePrefix):
        htmlResponsePath = os.path.join(email_sec_cache.configDir, filePrefix + ".html")
        if not os.access(htmlResponsePath, os.F_OK):
            
            plainTextResponsePath = os.path.join(email_sec_cache.configDir, filePrefix + ".txt")
            with open(plainTextResponsePath, "r") as plainTextResponseFile:
                plainTextResponse = plainTextResponseFile.read()
            plainText = email.mime.text.MIMEText(plainTextResponse, "plain")
            email_sec_cache.removeMimeVersion(plainText)
            return plainText
            
        with open(htmlResponsePath, "r") as htmlResponseFile:
            htmlResponse = htmlResponseFile.read()
            
        h = html2text.HTML2Text()
        h.ignore_links = True
        plainTextResponse = h.handle(htmlResponse)
            
        multipartAlt = email.mime.multipart.MIMEMultipart("alternative")
        email_sec_cache.removeMimeVersion(multipartAlt)
        plainText = email.mime.text.MIMEText(plainTextResponse, "plain")
        email_sec_cache.removeMimeVersion(plainText)
        html = email.mime.text.MIMEText(htmlResponse, "html")
        email_sec_cache.removeMimeVersion(html)
        multipartAlt.attach(plainText)            
        multipartAlt.attach(html)
        
        return multipartAlt
    
    def constructSpoilerMessagePart(self, filePrefix):
        spoilerPicturePath = os.path.join(email_sec_cache.configDir, filePrefix + "Spoiler.jpg")
        with open(spoilerPicturePath, "rb") as spoilerPictureFile:
            spoilerPicture = spoilerPictureFile.read()
        spoilerPictureAttachment = email.mime.image.MIMEImage(spoilerPicture)
        email_sec_cache.removeMimeVersion(spoilerPictureAttachment)
        email_sec_cache.setMimeAttachmentFileName(spoilerPictureAttachment, "spoiler.jpg")
        return spoilerPictureAttachment
