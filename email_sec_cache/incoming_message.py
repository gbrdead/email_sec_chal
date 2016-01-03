# -*- coding: utf-8 -*-
import email.utils
import email_sec_cache
import bs4
import logging
import cgi
import gpgmime
import re



class IncomingMessagePart:
    
    incomingMessage = None

    isEncrypted = False
    isVerified = False
    isForImpostor = False

    msgPart = None    
    plainText = None
    
    def extractPlainText(self):
        if self.plainText is not None:
            return
        
        if self.msgPart.get_content_maintype() != "text":
            logging.warning(u"EmailSecCache: A non-text part in a message from %s with id %s encountered" % (self.incomingMessage.emailAddress, self.incomingMessage.id))
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
                logging.warning(u"EmailSecCache: No charset specified for a part in a message from %s with id %s; assuming UTF-8" % (self.incomingMessage.emailAddress, self.incomingMessage.id))
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
        self.id = email_sec_cache.getHeaderAsUnicode(self.originalMessage, "Message-ID")
        
        from_ = email_sec_cache.getHeaderAsUnicode(self.originalMessage, "From")
        _, self.emailAddress = email.utils.parseaddr(from_)
        if not self.emailAddress:
            raise email_sec_cache.MsgException(u"Missing From header in message with id %s" % self.id)
        
        self.pgp = email_sec_cache.Pgp(self.emailAddress)
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        self.pgp.close()
        
    def getMessageParts(self):
        self.extractMessageParts()
        return self.messageParts
    
    @staticmethod
    def create(message):
        if gpgmime.is_encrypted(message) or gpgmime.is_signed(message):
            return PgpMimeIncomingMessage(message)
        return PgpInlineIncomingMessage(message)
    
    def extractMessagePartsRecursive(self, msg):
        if msg.is_multipart():
            msgParts = []
            for payload in msg.get_payload():
                msgParts += self.extractMessagePartsRecursive(payload)
            return msgParts
        
        if msg.get_content_maintype() == "multipart":
            return self.extractMessagePartsRecursive(msg.get_payload())        
        
        contentDisposition = msg["Content-Disposition"]
        if contentDisposition is not None:
            contentDispositionValue, _ = cgi.parse_header(contentDisposition)
            if contentDispositionValue == "attachment":
                return []
            
        return [self.processSinglePartMessage(msg)]


class PgpMimeIncomingMessage(IncomingMessage):
    
    isEncrypted = False
    isVerified = False
    isForImpostor = False
    
    plainMessage = None

    
    def __init__(self, originalMessage_):
        IncomingMessage.__init__(self, originalMessage_)
        
    def decryptAndVerify(self):
        if self.plainMessage is not None:
            return
        
        logging.debug(u"EmailSecCache: Parsing a message with id %s from %s" % (self.id, self.emailAddress))
        self.isEncrypted, self.isVerified, self.plainMessage, self.isForImpostor = self.pgp.parseMessage(self.originalMessage)
        logging.debug(u"EmailSecCache: The message with id %s was %sencrypted and %sverified" % (self.id, (u"" if self.isEncrypted else u"not "), (u"" if self.isVerified else u"not ")))
        
    def extractMessageParts(self):
        if self.messageParts is not None:
            return
        self.decryptAndVerify()
        self.messageParts = self.extractMessagePartsRecursive(self.plainMessage)
        
    def processSinglePartMessage(self, msg):
        msgPart = IncomingMessagePart()
        msgPart.incomingMessage = self
        msgPart.isEncrypted = self.isEncrypted
        msgPart.isVerified = self.isVerified
        msgPart.isForImpostor = self.isForImpostor
        msgPart.msgPart = msg
        return msgPart



class PgpInlineIncomingMessage(IncomingMessage):
    
    def extractMessageParts(self):
        if self.messageParts is not None:
            return
        self.messageParts = self.extractMessagePartsRecursive(self.originalMessage)
        
    def processSinglePartMessage(self, msg):
        msgPart = IncomingMessagePart()
        msgPart.isEncrypted = False
        msgPart.isVerified = False
        msgPart.incomingMessage = self
        msgPart.msgPart = msg
        
        plainText = msgPart.getPlainText().strip()
        if self.isEncrypted(plainText):
            plainText = self.normalizePgpHtml(msg, plainText)
            
            decrypted = self.pgp.officialGpg.decrypt(plainText)
            if decrypted:
                msgPart.isEncrypted = True
                msgPart.isVerified = decrypted.valid
                msgPart.isForImpostor = False
                msgPart.plainText = unicode(decrypted)
            else:
                decrypted = self.pgp.impostorGpg.decrypt(plainText)
                if decrypted:
                    msgPart.isEncrypted = True
                    msgPart.isVerified = decrypted.valid
                    msgPart.isForImpostor = True
                    msgPart.plainText = unicode(decrypted)
                else:
                    raise email_sec_cache.PgpException(u"secret key not available")
        
        plainText = msgPart.getPlainText().strip()                
        if self.isSigned(plainText):
            plainText = self.normalizePgpHtml(msg, plainText)
            
            decrypted = self.pgp.officialGpg.decrypt(plainText)
            msgPart.isVerified = decrypted.valid
            msgPart.plainText = unicode(decrypted)
        
        return msgPart


    def isEncrypted(self, plainText):
        return plainText.startswith("-----BEGIN PGP MESSAGE-----")
        
    def isSigned(self, plainText):
        return plainText.startswith("-----BEGIN PGP SIGNED MESSAGE-----")
    
    stripAroundNewlinesRe = re.compile(u"[ \t]*\n[ \t]*", re.UNICODE | re.MULTILINE)
    def normalizePgpHtml(self, msg, plainText):
        if msg.get_content_maintype() == "text" and msg.get_content_subtype() == "html":
            return self.stripAroundNewlinesRe.sub(u"\n", plainText)
        return plainText
