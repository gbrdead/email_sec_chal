import re

def extractWords(text):
    if not isinstance(text, list):
        return re.compile('\w+').findall(text)
    words = []
    for t in text:
        words += extractWords(t)
    return words
