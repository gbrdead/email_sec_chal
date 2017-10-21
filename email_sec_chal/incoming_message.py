# -*- coding: utf-8 -*-
import email_sec_chal
import bs4
import logging
import re
import email.mime.multipart



class IncomingMessagePart:
    
    incomingMessage = None

    encrypted = False
    signedAndVerified = False
    forImpostor = False

    msgPart = None    
    plainText = None
    
    
    stripAroundNewlinesRe = re.compile(" *\n *", re.MULTILINE)
    def extractPlainText(self):
        if self.plainText is not None:
            return
        
        if self.msgPart.get_content_maintype() != "text" and self.msgPart.get_content_type() != "application/pgp-keys":
            self.plainText = ""
            return
        
        self.plainText = self.msgPart.get_payload(decode=True)
        
        if self.msgPart.get_content_type() == "text/html":
            html = bs4.BeautifulSoup(self.plainText, "html.parser")
            for tag in html.find_all(["script", "style"]):
                tag.extract()
            for tag in html.find_all(string=True):
                if isinstance(tag, bs4.Comment):
                    tag.extract()
                else:
                    if not tag.find_parent("pre"):
                        tag.replace_with(str(tag).strip())
            for tag in html.find_all("br"):
                tag.insert_before("\n")
                tag.unwrap()
            self.plainText = html.get_text(separator=" ")
            self.plainText = self.stripAroundNewlinesRe.sub("\n", self.plainText)
            
        else:
            charset = self.msgPart.get_content_charset()
            if charset is None:
                logging.warning("EmailSecChal: incoming_message: No charset specified for a part in message from %s (%s); assuming UTF-8" % (self.incomingMessage.emailAddress, self.incomingMessage.id))
                charset = "utf-8"
            try:
                self.plainText = self.plainText.decode(charset, "ignore")
            except LookupError:
                logging.warning("EmailSecChal: incoming_message: Unknown charset: %s" % charset, exc_info=True)
                self.plainText = self.plainText.decode("utf-8", "ignore")
    
    def getPlainText(self):
        self.extractPlainText()
        return self.plainText



class IncomingMessage:
    
    id = None
    emailAddress = None
    originalMessage = None
    pgp = None

    
    def __init__(self, originalMessage_):
        self.originalMessage = originalMessage_
        self.id = self.originalMessage["Message-ID"]
        
        self.emailAddress = email_sec_chal.util.getMessageSenderEmailAddress(self.originalMessage)
        if not self.emailAddress:
            raise email_sec_chal.MsgException("Missing From header in incoming message (%s)" % self.id)
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        logging.debug("EmailSecChal: incoming_message: Closed message from %s (%s)" % (self.emailAddress, self.id))
        
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
        contentTypeValue, contentTypeParameters = email_sec_chal.util.getHeaderValue(message, "Content-Type")
        return \
            contentTypeValue == "multipart/encrypted" and \
            contentTypeParameters["protocol"] == "application/pgp-encrypted"
        
    @staticmethod
    def isPgpMimeSigned(message):
        contentTypeValue, contentTypeParameters = email_sec_chal.util.getHeaderValue(message, "Content-Type")
        return \
            contentTypeValue == "multipart/signed" and \
            contentTypeParameters["protocol"] == "application/pgp-signature"

    
    def extractMessagePartsRecursive(self, message, skipAttachments):
        if message.is_multipart():
            msgParts = []
            for payload in message.get_payload():
                msgParts += self.extractMessagePartsRecursive(payload, skipAttachments)
            return msgParts
        
        if skipAttachments:
            contentDispositionValue, _ = email_sec_chal.util.getHeaderValue(message, "Content-Disposition")
            if contentDispositionValue is not None:
                if contentDispositionValue == "attachment":
                    logging.debug("EmailSecChal: incoming_message: Ignoring attachment in message from %s (%s)" % (self.emailAddress, self.id))
                    return []
            
        incomingMsgPart = self.processSinglePartMessage(message)
        if incomingMsgPart is not None:
            return [incomingMsgPart]
        return []
    
    def getMessageParts(self, skipAtttachments=True):
        with email_sec_chal.Pgp(self.emailAddress) as self.pgp:
            return self.getMessagePartsInternal(skipAtttachments)
    
    def getPgpKeys(self):
        keyMarkers = [("-----BEGIN PGP PUBLIC KEY BLOCK-----", "-----END PGP PUBLIC KEY BLOCK-----"), ("-----BEGIN PGP PRIVATE KEY BLOCK-----", "-----END PGP PRIVATE KEY BLOCK-----")]
        
        pgpKeys = []
        for msgPart in self.getMessageParts(skipAtttachments=False):
            text = msgPart.getPlainText()
            
            for (pgpKeyBeginMarker, pgpKeyEndMarker) in keyMarkers:

                currentPos = 0
                while True: 
                    pgpKeyBeginPos = text.find(pgpKeyBeginMarker, currentPos)
                    if pgpKeyBeginPos < 0:
                        break
                    
                    pgpKeyEndPos = text.find(pgpKeyEndMarker, pgpKeyBeginPos + len(pgpKeyBeginMarker))
                    if pgpKeyEndPos < 0:
                        break
                    pgpKeyEndPos += len(pgpKeyEndMarker)
                    
                    pgpKeyText = text[pgpKeyBeginPos:pgpKeyEndPos]
                    pgpKeys.append(pgpKeyText)
                    
                    currentPos = pgpKeyEndPos 
        
        return pgpKeys
        


class PgpMimeIncomingMessage(IncomingMessage):
    
    encrypted = False
    signedAndVerified = False
    forImpostor = False
    plainMessage = None

    
    def __init__(self, originalMessage_):
        IncomingMessage.__init__(self, originalMessage_)
        logging.debug("EmailSecChal: incoming_message: Created message from %s (%s) as PGP/MIME" % (self.emailAddress, self.id))
        
    def decryptAndVerify(self):
        self.signedAndVerified = False
        self.plainMessage = self.originalMessage
        
        if self.isEncrypted():
            self.encrypted = True
            encryptedPayload = self.originalMessage.get_payload(1).get_payload()

            decryptedResult = self.pgp.officialGpg.decrypt(encryptedPayload)
            if decryptedResult:
                logging.debug("EmailSecChal: incoming_message: PGP/MIME message from %s (%s) was decrypted by the official bot's key" % \
                    (self.emailAddress, self.id))
                self.forImpostor = False
            else:
                decryptedResult = self.pgp.impostorGpg.decrypt(encryptedPayload)
                if decryptedResult:
                    logging.warning("EmailSecChal: incoming_message: PGP/MIME message from %s (%s) was decrypted by the impostor bot's key" % \
                        (self.emailAddress, self.id))
                    self.forImpostor = True
                else:
                    logging.warning("EmailSecChal: incoming_message: PGP/MIME message from %s (%s) could not be decrypted:\n%s" % \
                        (self.emailAddress, self.id, decryptedResult.stderr))
                    self.signedAndVerified = False
                    self.plainMessage = email.mime.multipart.MIMEMultipart()
                    return
                
            self.signedAndVerified = decryptedResult.valid
            self.plainMessage = email.message_from_bytes(decryptedResult.data)
            
        else:
            self.encrypted = False
            
        if self.isSigned():
            signature = self.plainMessage.get_payload(1).get_payload()
            self.plainMessage = self.plainMessage.get_payload(0)
            verifiedResult = self.pgp.verifyMessageWithDetachedSignature(self.plainMessage, signature)
            self.signedAndVerified = verifiedResult.valid
            
        logging.debug("EmailSecChal: incoming_message: PGP/MIME message from %s (%s) is %s and %s" % \
            (self.emailAddress, self.id, \
             "encrypted" if self.encrypted else "not encrypted", \
             "has a valid signature" if self.signedAndVerified else "does not have a valid signature"))
        
    def getMessagePartsInternal(self, skipAtttachments=True):
        self.decryptAndVerify()
        return self.extractMessagePartsRecursive(self.plainMessage, skipAtttachments)
        
    def processSinglePartMessage(self, msg):
        msgPart = IncomingMessagePart()
        msgPart.incomingMessage = self
        msgPart.encrypted = self.encrypted
        msgPart.signedAndVerified = self.signedAndVerified
        msgPart.forImpostor = self.forImpostor
        msgPart.msgPart = msg
        return msgPart
    
    def isEncrypted(self):
        return IncomingMessage.isPgpMimeEncrypted(self.plainMessage)
        
    def isSigned(self):
        return IncomingMessage.isPgpMimeSigned(self.plainMessage)
        


class PgpInlineIncomingMessage(IncomingMessage):
    
    def __init__(self, originalMessage_):
        IncomingMessage.__init__(self, originalMessage_)
        logging.debug("EmailSecChal: incoming_message: Created message from %s (%s) as inline PGP" % (self.emailAddress, self.id))
    
    def getMessagePartsInternal(self, skipAtttachments=True):
        return self.extractMessagePartsRecursive(self.originalMessage, skipAtttachments)
        
    def processSinglePartMessage(self, msg):
        msgPart = IncomingMessagePart()
        msgPart.incomingMessage = self
        msgPart.msgPart = msg
        
        plainText = self.normalize(msg, msgPart.getPlainText())
        if self.isEncrypted(plainText):
            msgPart.encrypted = True
            
            decryptedResult = self.pgp.officialGpg.decrypt(plainText)
            if decryptedResult:
                logging.debug("EmailSecChal: incoming_message: Inline PGP message from %s (%s) has a message part that was decrypted by the official bot's key" % \
                    (self.emailAddress, self.id))
                msgPart.forImpostor = False
            else:
                if decryptedResult.key_id is not None:    # So the message is not encrypted but just signed; the header is wrong.
                    logging.warning("EmailSecChal: incoming_message: Inline PGP message from %s (%s) has a message part with a wrong PGP header (\"PGP MESSAGE\" instead of \"PGP SIGNED MESSAGE\")" % \
                            (self.emailAddress, self.id))
                    msgPart.encrypted = False
                else:
                    decryptedResult = self.pgp.impostorGpg.decrypt(plainText)
                    if decryptedResult:
                        logging.warning("EmailSecChal: incoming_message: Inline PGP  message from %s (%s) has a message part that was decrypted by the impostor bot's key" % \
                            (self.emailAddress, self.id))
                        msgPart.forImpostor = True
                    else:
                        logging.warning("EmailSecChal: incoming_message: Inline PGP message from %s (%s) has a message part that could not be decrypted:\n%s" % \
                            (self.emailAddress, self.id, decryptedResult.stderr))
                        return None

            msgPart.signedAndVerified = decryptedResult.valid
            msgPart.plainText = str(decryptedResult)
               
        else:
            msgPart.encrypted = False
            msgPart.signedAndVerified = False
        
        plainText = self.normalize(msg, msgPart.getPlainText())                
        if self.isSigned(plainText):
            
            if msgPart.encrypted:
                logging.debug("EmailSecChal: incoming_message: Inline PGP message from %s (%s) has a message part that has been signed and encrypted in two separate steps" % \
                    (self.emailAddress, self.id))
            
            decryptedResult = self.pgp.officialGpg.decrypt(plainText)
            msgPart.signedAndVerified = decryptedResult.valid
            msgPart.plainText = str(decryptedResult)
            
        logging.debug("EmailSecChal: incoming_message: Inline PGP message from %s (%s) has a message part that is %s and %s" % \
            (self.emailAddress, self.id, \
             "encrypted" if msgPart.encrypted else "not encrypted", \
             "has a valid signature" if msgPart.signedAndVerified else "does not have a valid signature"))
        
        return msgPart


    def isEncrypted(self, plainText):
        return plainText.startswith("-----BEGIN PGP MESSAGE-----")
        
    def isSigned(self, plainText):
        return plainText.startswith("-----BEGIN PGP SIGNED MESSAGE-----") or \
            plainText.startswith("-----BEGIN PGP MESSAGE-----")     # GpgOL pre-3.0 sends a wrong header.
    
    def normalize(self, msg, plainText):
        # GpgOL pre-3.0 sends the armored PGP message after the clear text, in the same message part.
        # We will discard the clear text - it should be contained in the armored message as well (but signed).
        fixed = False        
        pgpMessageBeginPos = plainText.find("-----BEGIN PGP MESSAGE-----")
        pgpMessageEndPos = plainText.find("-----END PGP MESSAGE-----")
        if pgpMessageBeginPos > 0 and pgpMessageEndPos != -1:
            pgpMessageEndPos += len("-----END PGP MESSAGE-----")
            plainText = plainText[pgpMessageBeginPos:pgpMessageEndPos]
            fixed = True
        else:
            pgpMessageBeginPos = plainText.find("-----BEGIN PGP SIGNED MESSAGE-----")
            pgpMessageEndPos = plainText.find("-----END PGP SIGNATURE-----")    # This is not a typo. A PGP signed message ends with the signature, there is no "END PGP SIGNED MESSAGE". 
            if pgpMessageBeginPos > 0 and pgpMessageEndPos != -1:
                pgpMessageEndPos += len("-----END PGP SIGNATURE-----")
                plainText = plainText[pgpMessageBeginPos:pgpMessageEndPos]
                fixed = True
        if fixed:
            logging.warning("EmailSecChal: incoming_message: Inline PGP message from %s (%s) has a PGP armored message not in the beginning of its containing message part" % \
                (self.emailAddress, self.id))
            
        return plainText
