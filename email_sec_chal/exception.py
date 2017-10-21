# -*- coding: utf-8 -*-


class EmailSecChalException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class MsgException(EmailSecChalException):
    pass

class PgpException(EmailSecChalException):
    pass
