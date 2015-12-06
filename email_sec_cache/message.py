import email.utils
import email_sec_cache
import bs4
import logging


class MsgException(email_sec_cache.EmailSecCacheException):
    pass


class Message:
    
    id = None
    emailAddress = None
    originalMessage = None
    plainMessage = None
    isEncrypted = False
    isVerified = False
    
    def __init__(self, originalMessage_, gpgVerbose = False):
        self.originalMessage = originalMessage_
        
        _, self.emailAddress = email.utils.parseaddr(self.originalMessage["From"])
        if not self.emailAddress:
            raise MsgException("Missing From header in message: %s" % self.originalMessage)
        self.id = self.originalMessage["Message-ID"]
        
        logging.info("Parsing a message with id %s from %s" % (self.id, self.emailAddress))

        with email_sec_cache.Pgp(self.emailAddress, gpgVerbose) as pgp:
            self.isEncrypted, self.isVerified, self.plainMessage = pgp.parseMessage(self.originalMessage)
        logging.info("The message with id %s was %sencrypted and %sverified" % (self.id, ("" if self.isEncrypted else "not "), ("" if self.isVerified else "not ")))
            
    def getMessageTexts(self):
        return self.getMessageTextsAux(self.plainMessage)
        
    def getMessageTextsAux(self, msg):
        if msg.is_multipart():
            texts = []
            for payload in msg.get_payload():
                texts += self.getMessageTextsAux(payload)
            return texts
        
        if msg.get_content_maintype() == "multipart":
            return self.getMessageTextsAux(msg.get_payload())        
        
        plainText = self.convertToPlainText(msg)
        if plainText is not None:
            return [plainText]
        else:
            return []
        
    def convertToPlainText(self, msg):
        if msg.get_content_maintype() != "text":
            logging.warning("A non-text part in a message from %s with id %s encountered (possible spam)" % (self.emailAddress, self.id))
            return None
        
        text = msg.get_payload(decode=True)
        if msg.get_content_subtype() == "html":
            html = bs4.BeautifulSoup(text, "html.parser")
            for el in html.findAll(["script", "style"]):
                el.extract()
            plainText = html.get_text(separator=" ")
        else:
            charset = msg.get_content_charset()
            if charset is None:
                logging.warning("No charset specified for a message from %s with id %s; assuming UTF-8" % (self.emailAddress, self.id))
                charset = "utf-8"
            plainText = text.decode(charset, "ignore")
        return plainText
        