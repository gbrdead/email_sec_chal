import email.utils
import email_sec_cache
import bs4
import logging
import email.mime.multipart
import email.header


class MsgException(email_sec_cache.EmailSecCacheException):
    pass


def getHeaderAsUnicode(msg, headerName):
    headerAsStr = msg[headerName]
    if headerAsStr is None:
        return u""
    header = email.header.make_header(
        email.header.decode_header(headerAsStr))
    return unicode(header)

def setHeaderFromUnicode(msg, headerName, value):
    msg[headerName] = email.header.Header(value, "utf-8").encode()

def getReSubject(msg):
    subject = getHeaderAsUnicode(msg, "Subject")
    if not subject:
        subject = u"Re:"
    else:
        if not subject.lower().startswith(u"re:"):
            subject = u"Re: " + subject
    return subject
    

class IncomingMessage:
    
    id = None
    emailAddress = None
    originalMessage = None
    plainMessage = None
    isEncrypted = False
    isVerified = False
    isForImpostor = False
    
    def __init__(self, originalMessage_, gpgVerbose = False):
        self.originalMessage = originalMessage_
        
        from_ = email_sec_cache.getHeaderAsUnicode(self.originalMessage, "From")
        _, self.emailAddress = email.utils.parseaddr(from_) 
        if not self.emailAddress:
            raise MsgException(u"Missing From header in message: %s" % self.originalMessage)
        self.id = email_sec_cache.getHeaderAsUnicode(self.originalMessage, "Message-ID")
        
        logging.debug(u"Parsing a message with id %s from %s" % (self.id, self.emailAddress))

        with email_sec_cache.Pgp(self.emailAddress, gpgVerbose) as pgp:
            self.isEncrypted, self.isVerified, self.plainMessage, self.isForImpostor = pgp.parseMessage(self.originalMessage)
        logging.debug(u"The message with id %s was %sencrypted and %sverified" % (self.id, (u"" if self.isEncrypted else u"not "), (u"" if self.isVerified else u"not ")))
            
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
            logging.warning(u"A non-text part in a message from %s with id %s encountered (possible spam)" % (self.emailAddress, self.id))
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
                logging.warning(u"No charset specified for a part in a message from %s with id %s; assuming UTF-8" % (self.emailAddress, self.id))
                charset = "utf-8"
            plainText = text.decode(charset, "ignore")
        return plainText
    
    
class OutgoingMessage:
    
    msg = None
    
    def __init__(self, incomingMsg):
        
        self.msg = email.mime.multipart.MIMEMultipart()
        
        self.msg["To"] = incomingMsg.plainMessage["From"]
        
        subject = getReSubject(incomingMsg.plainMessage)
        setHeaderFromUnicode(self.msg, "Subject", subject) 
