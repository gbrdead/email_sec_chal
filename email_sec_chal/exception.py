# -*- coding: utf-8 -*-


class EmailSecCacheException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class MsgException(EmailSecCacheException):
    pass

class PgpException(EmailSecCacheException):
    pass
