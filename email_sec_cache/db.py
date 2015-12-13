# -*- coding: utf-8 -*-
import email_sec_cache
import os
import sqlite3
import logging


class Db:
    
    initialized = False
    conn = None
    
    
    @staticmethod
    def staticInit():
        if Db.initialized:
            return
        
        if not os.access(email_sec_cache.dataDir, os.F_OK):
            os.makedirs(email_sec_cache.dataDir)

        Db.conn = sqlite3.connect(os.path.join(email_sec_cache.dataDir, u"email_sec_cache.sqlite3"), isolation_level=None)
        cursor = Db.conn.cursor()
        cursor.execute(u"""
            CREATE TABLE IF NOT EXISTS correspondents (
                email_address TEXT PRIMARY KEY,
                key TEXT DEFAULT NULL,
                red_herring_sent INTEGER DEFAULT 0)""")
        logging.debug(u"Created the correspondents DB table")
        
        Db.initialized = True

    def __init__(self):
        Db.staticInit()
        
    def correspondentExists(self, emailAddress):
        cursor = Db.conn.cursor()
        cursor.execute(u"SELECT COUNT(*) FROM correspondents WHERE email_address = ?", (emailAddress, ))
        count = cursor.fetchone()[0]
        return count > 0
            
    def getCorrespondentKey(self, emailAddress):
        cursor = Db.conn.cursor()
        cursor.execute(u"SELECT key FROM correspondents WHERE email_address = ?", (emailAddress, ))
        row = cursor.fetchone()
        if row is not None:
            return row[0]
        return None
    
    def setCorrespondentKey(self, emailAddress, key):
        cursor = Db.conn.cursor()
        if not self.correspondentExists(emailAddress):
            if key is not None:
                cursor.execute(u"INSERT INTO correspondents (email_address, key) VALUES(?, ?)", (emailAddress, key))
                logging.debug(u"Added a new correspondent key in the DB for %s" % emailAddress)
        else:
            cursor.execute(u"UPDATE correspondents SET key = ? WHERE email_address = ?", (key, emailAddress))
            logging.debug(u"Updated the correspondent key in the DB for %s" % emailAddress)

    def isRedHerringSent(self, emailAddress):
        cursor = Db.conn.cursor()
        cursor.execute(u"SELECT red_herring_sent FROM correspondents WHERE email_address = ?", (emailAddress, ))
        row = cursor.fetchone()
        if row is not None:
            return row[0] != 0
        return False
    
    def redHerringSent(self, emailAddress):
        cursor = Db.conn.cursor()
        if not self.correspondentExists(emailAddress):
            cursor.execute(u"INSERT INTO correspondents (email_address, red_herring_sent) VALUES(?, ?)", (emailAddress, 1))
        else:
            cursor.execute(u"UPDATE correspondents SET red_herring_sent = ? WHERE email_address = ?", (1, emailAddress))
        logging.debug(u"Set red herring as sent in DB for %s" % emailAddress)
