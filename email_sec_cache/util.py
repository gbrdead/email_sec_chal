# -*- coding: utf-8 -*-
import re
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


def removeFile(fileName):
    try:
        logging.debug("EmailSecCache: Removing file: %s" % fileName)
        os.remove(fileName)
    except:
        logging.warning("EmailSecCache: Cannot remove file %s" % fileName, exc_info=True)

def removeMimeVersion(msgPart):
    del msgPart["MIME-Version"]

def setMimeAttachmentFileName(mimeMsgPart, fileName):
    mimeMsgPart.set_param("name", fileName)
    mimeMsgPart.add_header("Content-Disposition", "attachment", filename=fileName)
