# -*- coding: utf-8 -*-
import re
import logging
import os.path
import cgi
import email.utils


wordRe = re.compile("\\w+")

def extractWords(text):
    if not isinstance(text, list):
        return wordRe.findall(text)
    words = []
    for t in text:
        words += extractWords(t)
    return words


def removeFile(fileName):
    try:
        logging.debug("EmailSecChal: util: Removing file: %s" % fileName)
        os.remove(fileName)
    except:
        logging.warning("EmailSecChal: util: Cannot remove file %s" % fileName, exc_info=True)


def removeMimeVersion(msgPart):
    del msgPart["MIME-Version"]

def setMimeAttachmentFileName(mimeMsgPart, fileName):
    mimeMsgPart.set_param("name", fileName)
    mimeMsgPart.add_header("Content-Disposition", "attachment", filename=fileName)


def isPathPrefix(path, prefixPath):
    prefixPath = os.path.abspath(prefixPath)
    prefixPath = os.path.normcase(prefixPath)
    prefixPath = os.path.join(prefixPath, "") # Ensures that the path ends with a slash.
    
    path = os.path.abspath(path)
    path = os.path.normcase(path)
    
    return path.startswith(prefixPath)


def getHeaderValue(message, headerName):
    header = message[headerName]
    if isinstance(header, str):
        return cgi.parse_header(header)
    return None, None

def getMessageRecipientsEmailAddresses(message):
    to = message.get_all("To", [])
    cc = message.get_all("CC", [])
    bcc = message.get_all("BCC", [])
    parsedRecipientAddresses = email.utils.getaddresses(to + cc + bcc)
    
    recipientEmailAddresses = set()
    for _, emailAddress in parsedRecipientAddresses:
        recipientEmailAddresses.add(emailAddress.lower())
    return recipientEmailAddresses

def getMessageSenderEmailAddress(message):
    from_ = message.get("From")
    if from_ is None:
        return None
    _, emailAddress = email.utils.parseaddr(from_)
    if emailAddress is None:
        return None
    return emailAddress.lower()
