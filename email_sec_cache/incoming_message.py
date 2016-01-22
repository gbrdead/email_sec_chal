# -*- coding: utf-8 -*-
import email.utils
import email_sec_cache
import bs4
import logging
import cgi
import re
import email.mime.multipart



class IncomingMessagePart:
    
    incomingMessage = None

    encrypted = False
    signedAndVerified = False
    forImpostor = False

    msgPart = None    
    plainText = None
    
    def extractPlainText(self):
        if self.plainText is not None:
            return
        
        if self.msgPart.get_content_maintype() != "text":
            logging.warning("EmailSecCache: A non-text part in incoming message from %s (%s) encountered" % (self.incomingMessage.emailAddress, self.incomingMessage.id))
            self.plainText = ""
            return
        
        text = self.msgPart.get_payload(decode=True)
        if self.msgPart.get_content_subtype() == "html":
            html = bs4.BeautifulSoup(text, "html.parser")
            for el in html.findAll(["script", "style"]):
                el.extract()
            self.plainText = html.get_text(separator=" ")
        else:
            charset = self.msgPart.get_content_charset()
            if charset is None:
                logging.warning("EmailSecCache: No charset specified for a part in incoming message from %s (%s); assuming UTF-8" % (self.incomingMessage.emailAddress, self.incomingMessage.id))
                charset = "utf-8"
            self.plainText = text.decode(charset, "ignore")
    
    def getPlainText(self):
        self.extractPlainText()
        return self.plainText



class IncomingMessage:
    
    id = None
    emailAddress = None
    originalMessage = None
    pgp = None
    messageParts = None

    
    def __init__(self, originalMessage_):
        self.originalMessage = originalMessage_
        self.id = self.originalMessage["Message-ID"]
        
        from_ = self.originalMessage["From"]
        _, self.emailAddress = email.utils.parseaddr(from_)
        if not self.emailAddress:
            raise email_sec_cache.MsgException("Missing From header in incoming message (%s)" % self.id)
        
        self.pgp = email_sec_cache.Pgp(self.emailAddress)
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        self.pgp.close()
        logging.debug("EmailSecCache: Closed incoming message from %s (%s)" % (self.emailAddress, self.id))
        
    def getMessageParts(self):
        self.extractMessageParts()
        return self.messageParts
    
    @staticmethod
    def create(message):
        if IncomingMessage.isPgpMime(message):
            return PgpMimeIncomingMessage(message)
        return PgpInlineIncomingMessage(message)
    
    @staticmethod
    def isPgpMime(message):
        return IncomingMessage.isPgpMimeEncrypted(message) or IncomingMessage.isPgpMimeSigned(message)
    
    @staticmethod
    def isPgpMimeEncrypted(message):
        contentType = message["Content-Type"]
        contentTypeValue, contentTypeParameters = cgi.parse_header(contentType)
        return \
            contentTypeValue == "multipart/encrypted" and \
            contentTypeParameters["protocol"] == "application/pgp-encrypted"
        
    @staticmethod
    def isPgpMimeSigned(message):
        contentType = message["Content-Type"]
        contentTypeValue, contentTypeParameters = cgi.parse_header(contentType)
        return \
            contentTypeValue == "multipart/signed" and \
            contentTypeParameters["protocol"] == "application/pgp-signature"

    
    def extractMessagePartsRecursive(self, msg):
        if msg.is_multipart():
            msgParts = []
            for payload in msg.get_payload():
                msgParts += self.extractMessagePartsRecursive(payload)
            return msgParts
        
        contentDisposition = msg["Content-Disposition"]
        if contentDisposition is not None:
            contentDispositionValue, _ = cgi.parse_header(contentDisposition)
            if contentDispositionValue == "attachment":
                logging.debug("EmailSecCache: Ignoring attachment in incoming message from %s (%s)" % (self.emailAddress, self.id))
                return []
            
        incomingMsgPart = self.processSinglePartMessage(msg)
        if incomingMsgPart is not None:
            return [incomingMsgPart]
        return []


class PgpMimeIncomingMessage(IncomingMessage):
    
    encrypted = False
    signedAndVerified = False
    forImpostor = False
    plainMessage = None

    
    def __init__(self, originalMessage_):
        IncomingMessage.__init__(self, originalMessage_)
        logging.debug("EmailSecCache: Created incoming message from %s (%s) as PGP/MIME" % (self.emailAddress, self.id))
        
    def decryptAndVerify(self):
        self.signedAndVerified = False
        self.plainMessage = self.originalMessage
        
        if self.isEncrypted():
            self.encrypted = True
            encryptedPayload = self.originalMessage.get_payload(1).get_payload()

            decryptedResult = self.pgp.officialGpg.decrypt(encryptedPayload)
            if decryptedResult:
                logging.debug("EmailSecCache: PGP/MIME incoming message from %s (%s) was decrypted by the official bot's key" % \
                    (self.emailAddress, self.id))
                self.forImpostor = False
            else:
                decryptedResult = self.pgp.impostorGpg.decrypt(encryptedPayload)
                if decryptedResult:
                    logging.warning("EmailSecCache: PGP/MIME incoming message from %s (%s) was decrypted by the impostor bot's key" % \
                        (self.emailAddress, self.id))
                    self.forImpostor = True
                else:
                    logging.warning("EmailSecCache: PGP/MIME incoming message from %s (%s) could not be decrypted:\n%s" % \
                        (self.emailAddress, self.id, decryptedResult.stderr))
                    self.signedAndVerified = False
                    self.plainMessage = email.mime.multipart.MIMEMultipart()
                    return
                
            self.signedAndVerified = decryptedResult.valid
            self.plainMessage = email.message_from_string(str(decryptedResult))
            
        else:
            self.encrypted = False
            
            if self.isSigned():
                self.plainMessage = self.originalMessage.get_payload(0)
                signature = self.originalMessage.get_payload(1).get_payload()
                verifiedResult = self.pgp.verifyDataWithDetachedSignature(self.plainMessage, signature)
                self.signedAndVerified = verifiedResult.valid
            
        logging.debug("EmailSecCache: PGP/MIME incoming message from %s (%s) is %s and %s" % \
            (self.emailAddress, self.id, \
             "encrypted" if self.encrypted else "not encrypted", \
             "has a valid signature" if self.signedAndVerified else "does not have a valid signature"))
        
    def extractMessageParts(self):
        if self.messageParts is not None:
            return
        self.decryptAndVerify()
        self.messageParts = self.extractMessagePartsRecursive(self.plainMessage)
        
    def processSinglePartMessage(self, msg):
        msgPart = IncomingMessagePart()
        msgPart.incomingMessage = self
        msgPart.encrypted = self.encrypted
        msgPart.signedAndVerified = self.signedAndVerified
        msgPart.forImpostor = self.forImpostor
        msgPart.msgPart = msg
        return msgPart
    
    def isEncrypted(self):
        return IncomingMessage.isPgpMimeEncrypted(self.originalMessage)
        
    def isSigned(self):
        return IncomingMessage.isPgpMimeSigned(self.originalMessage)
        


class PgpInlineIncomingMessage(IncomingMessage):
    
    def __init__(self, originalMessage_):
        IncomingMessage.__init__(self, originalMessage_)
        logging.debug("EmailSecCache: Created incoming message from %s (%s) as inline PGP" % (self.emailAddress, self.id))
    
    def extractMessageParts(self):
        if self.messageParts is not None:
            return
        self.messageParts = self.extractMessagePartsRecursive(self.originalMessage)
        
    def processSinglePartMessage(self, msg):
        msgPart = IncomingMessagePart()
        msgPart.incomingMessage = self
        msgPart.msgPart = msg
        
        plainText = msgPart.getPlainText().strip()
        if self.isEncrypted(plainText):
            msgPart.encrypted = True
            plainText = self.normalizePgpHtml(msg, plainText)
            
            decryptedResult = self.pgp.officialGpg.decrypt(plainText)
            if decryptedResult:
                logging.debug("EmailSecCache: Inline PGP incoming message from %s (%s) has a message part that was decrypted by the official bot's key" % \
                    (self.emailAddress, self.id))
                msgPart.forImpostor = False
            else:
                decryptedResult = self.pgp.impostorGpg.decrypt(plainText)
                if decryptedResult:
                    logging.warning("EmailSecCache: Inline PGP incoming message from %s (%s) has a message part that was decrypted by the impostor bot's key" % \
                        (self.emailAddress, self.id))
                    msgPart.forImpostor = True
                else:
                    logging.warning("EmailSecCache: Inline PGP incoming message from %s (%s) has a message part that could not be decrypted:\n%s" % \
                        (self.emailAddress, self.id, decryptedResult.stderr))
                    return None

            msgPart.signedAndVerified = decryptedResult.valid
            msgPart.plainText = str(decryptedResult)
               
        else:
            msgPart.encrypted = False
            msgPart.signedAndVerified = False
        
        plainText = msgPart.getPlainText().strip()                
        if self.isSigned(plainText):
            
            if msgPart.encrypted:
                logging.debug("EmailSecCache: Inline PGP incoming message from %s (%s) has a message part that has been signed and encrypted in two separate steps" % \
                    (self.emailAddress, self.id))
            
            plainText = self.normalizePgpHtml(msg, plainText)
            
            decryptedResult = self.pgp.officialGpg.decrypt(plainText)
            msgPart.signedAndVerified = decryptedResult.valid
            msgPart.plainText = str(decryptedResult)
            
        logging.debug("EmailSecCache: Inline PGP incoming message from %s (%s) has a message part that is %s and %s" % \
            (self.emailAddress, self.id, \
             "encrypted" if msgPart.encrypted else "not encrypted", \
             "has a valid signature" if msgPart.signedAndVerified else "does not have a valid signature"))
        
        return msgPart


    def isEncrypted(self, plainText):
        return plainText.startswith("-----BEGIN PGP MESSAGE-----")
        
    def isSigned(self, plainText):
        return plainText.startswith("-----BEGIN PGP SIGNED MESSAGE-----")
    
    stripAroundNewlinesRe = re.compile("[ \t]*\n[ \t]*", re.MULTILINE)
    def normalizePgpHtml(self, msg, plainText):
        if msg.get_content_maintype() == "text" and msg.get_content_subtype() == "html":
            return self.stripAroundNewlinesRe.sub("\n", plainText)
        return plainText
