# -*- coding: utf-8 -*-
import email_sec_chal 
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
        self.pgp = email_sec_chal.Pgp(self.incomingMsg.emailAddress)
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        self.pgp.close()
        logging.debug("EmailSecChal: outgoing_message: Closed message to %s" % self.incomingMsg.emailAddress)
        
    def send(self, asImpostor):
        msg = self.construct(asImpostor)
        
        with self.createSmtpClient() as smtpClient:
            smtpClient.sendmail(email_sec_chal.Pgp.botEmailAddress, self.incomingMsg.emailAddress, msg.as_string())
            logging.debug("EmailSecChal: outgoing_message: Successfully sent message to %s" % self.incomingMsg.emailAddress)
        
    def createSmtpClient(self):
        smtpClient = smtplib.SMTP(email_sec_chal.smtpServerHost)
        logging.debug("EmailSecChal: outgoing_message: Successfully connected to SMTP server at %s" % email_sec_chal.smtpServerHost)
        return smtpClient
        
    def construct(self, asImpostor):
        msg = self.constructUnencrypted(asImpostor)
        logging.debug("EmailSecChal: outgoing_message: Unencrypted message to % successfully created" % self.incomingMsg.emailAddress)
        msg = self.pgp.signAndEncrypt(msg, asImpostor)
        logging.debug("EmailSecChal: outgoing_message: Message to % successfully signed and encrypted" % self.incomingMsg.emailAddress)
        
        msg["To"] = self.incomingMsg.originalMessage["From"]
        msg["From"] = email_sec_chal.Pgp.botFrom
        msg["Subject"] = getReSubject(self.incomingMsg.originalMessage)
        
        return msg
        
    def constructUnencrypted(self, asImpostor):
        if asImpostor:
            filePrefix = "impostor"
        else:
            filePrefix = "official"
            
        msg = email.mime.multipart.MIMEMultipart("mixed")
        email_sec_chal.removeMimeVersion(msg)
        
        text = self.constructTextMessagePart(filePrefix)
        msg.attach(text)
        logging.debug("EmailSecChal: outgoing_message: Text attached")
        
        spoilerPictureAttachment = self.constructSpoilerMessagePart(filePrefix)
        msg.attach(spoilerPictureAttachment)
        logging.debug("EmailSecChal: outgoing_message: Spoiler picture attached")
        
        if asImpostor:
            impostorPublicKey = self.pgp.getImpostorPublicKey()
            impostorPublicKeyAttachment = email.mime.application.MIMEApplication(impostorPublicKey, "pgp-keys", email.encoders.encode_quopri)
            email_sec_chal.removeMimeVersion(impostorPublicKeyAttachment)
            email_sec_chal.setMimeAttachmentFileName(impostorPublicKeyAttachment, "public_key.asc")
            msg.attach(impostorPublicKeyAttachment)

            logging.debug("EmailSecChal: outgoing_message: Applying Enigmail pre-1.9 workaround")
            msg.as_string()
            boundary = msg.get_boundary()
            boundary = "--" + boundary[2:]
            msg.set_boundary(boundary)
            
            logging.debug("EmailSecChal: outgoing_message: Impostor public key attached")
            
        return msg

    def constructTextMessagePart(self, filePrefix):
        htmlResponsePath = os.path.join(email_sec_chal.resourceDir, filePrefix + ".html")
        if not os.access(htmlResponsePath, os.F_OK):
            
            logging.debug("EmailSecChal: outgoing_message: %s not available, will use plain text" % htmlResponsePath)
            plainTextResponsePath = os.path.join(email_sec_chal.resourceDir, filePrefix + ".txt")
            with open(plainTextResponsePath, "r", encoding="utf-8") as plainTextResponseFile:
                plainTextResponse = plainTextResponseFile.read()
            plainText = email.mime.text.MIMEText(plainTextResponse, "plain")
            email_sec_chal.removeMimeVersion(plainText)
            return plainText
            
        with open(htmlResponsePath, "r", encoding="utf-8") as htmlResponseFile:
            htmlResponse = htmlResponseFile.read()
            
        h = html2text.HTML2Text()
        h.ignore_links = True
        plainTextResponse = h.handle(htmlResponse)
            
        multipartAlt = email.mime.multipart.MIMEMultipart("alternative")
        email_sec_chal.removeMimeVersion(multipartAlt)
        plainText = email.mime.text.MIMEText(plainTextResponse, "plain")
        email_sec_chal.removeMimeVersion(plainText)
        html = email.mime.text.MIMEText(htmlResponse, "html")
        email_sec_chal.removeMimeVersion(html)
        multipartAlt.attach(plainText)            
        multipartAlt.attach(html)
        
        return multipartAlt
    
    def constructSpoilerMessagePart(self, filePrefix):
        spoilerPicturePath = os.path.join(email_sec_chal.resourceDir, filePrefix + "Spoiler.jpg")
        with open(spoilerPicturePath, "rb") as spoilerPictureFile:
            spoilerPicture = spoilerPictureFile.read()
        spoilerPictureAttachment = email.mime.image.MIMEImage(spoilerPicture)
        email_sec_chal.removeMimeVersion(spoilerPictureAttachment)
        email_sec_chal.setMimeAttachmentFileName(spoilerPictureAttachment, "spoiler.jpg")
        return spoilerPictureAttachment
