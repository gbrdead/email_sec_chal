# -*- coding: utf-8 -*-
import re
import email.header
import os
import logging


wordRe = re.compile("\w+")

def extractWords(text):
    if not isinstance(text, list):
        return wordRe.findall(text)
    words = []
    for t in text:
        words += extractWords(t)
    return words


def getHeaderAsUnicode(msg, headerName):
    headerAsStr = msg[headerName]
    if headerAsStr is None:
        return ""
    header = email.header.make_header(
        email.header.decode_header(headerAsStr))
    return str(header)

def setHeaderFromUnicode(msg, headerName, value):
    msg[headerName] = email.header.Header(value, "utf-8").encode()


def removeFile(fileName):
    try:
        logging.debug("EmailSecCache: Removing file: %s" % fileName)
        os.remove(fileName)
    except:
        logging.warning("EmailSecCache: Cannot remove file %s" % fileName, exc_info=True)
