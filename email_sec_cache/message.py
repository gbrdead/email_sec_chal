import email.utils
import email_sec_cache
import bs4


class MsgException(email_sec_cache.EmailSecCacheException):
    pass


class Message:
    
    originalMessage = None
    plainMessage = None
    isEncrypted = False
    isVerified = False
    
    def __init__(self, originalMessage_, gpgVerbose = False):
        self.originalMessage = originalMessage_
        
        _, emailAddress = email.utils.parseaddr(self.originalMessage["From"])
        if not emailAddress:
            raise MsgException("Missing From header in message: %s" % self.originalMessage)

        with email_sec_cache.Pgp(emailAddress, gpgVerbose) as pgp:
            self.isEncrypted, self.isVerified, self.plainMessage = pgp.parseMessage(self.originalMessage)
            
    def getMessageTexts(self):
        return self.getMessageTextsAux(self.plainMessage)
        
    def getMessageTextsAux(self, msg):
        if msg.is_multipart():
            texts = []
            for payload in msg.get_payload():
                texts += self.getMessageTextsAux(payload)
            return texts
        else:
            plainText = self.convertToPlainText(msg)
            if plainText is not None:
                return [plainText]
            else:
                return []
        
    def convertToPlainText(self, msg):
        if msg.get_content_maintype() != "text":
            return None
        text = msg.get_payload(decode=True)
        if msg.get_content_subtype() == "html":
            plainText = bs4.BeautifulSoup(text, "lxml").get_text()
        else:
            plainText = text.decode(msg.get_content_charset(), "ignore")
        return plainText
        