# -*- coding: utf-8 -*-
import re
import email.header


wordRe = re.compile("\w+", re.UNICODE)

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
