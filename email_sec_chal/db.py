# -*- coding: utf-8 -*-
import email_sec_chal
import os
import sqlite3
import logging
import time


class Db:
    
    initialized = False
    conn = None
    
    
    @staticmethod
    def createDbConnection():
        return sqlite3.connect(os.path.join(email_sec_chal.dataDir, "email_sec_chal.sqlite3"), isolation_level=None)
        
    @staticmethod
    def staticInit():
        if Db.initialized:
            return
        
        if not os.access(email_sec_chal.dataDir, os.F_OK):
            os.makedirs(email_sec_chal.dataDir)

        conn = Db.createDbConnection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS correspondents (
                email_address TEXT PRIMARY KEY,
                key TEXT DEFAULT NULL,
                red_herring_sent INTEGER DEFAULT -1)""")
        logging.debug("EmailSecChal: db: Created the correspondents DB table")
        
        logging.debug("EmailSecChal: db: Static initialization successful")
        Db.initialized = True

    def __init__(self):
        Db.staticInit()
        self.conn = Db.createDbConnection()
        
    def getCorrespondentsCount(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM correspondents")
        return cursor.fetchone()[0]
        
    def correspondentExists(self, emailAddress):
        emailAddress = emailAddress.lower()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM correspondents WHERE email_address = ?", (emailAddress, ))
        count = cursor.fetchone()[0]
        return count > 0
            
    def getCorrespondentKey(self, emailAddress):
        emailAddress = emailAddress.lower()
        cursor = self.conn.cursor()
        cursor.execute("SELECT key FROM correspondents WHERE email_address = ?", (emailAddress, ))
        row = cursor.fetchone()
        if row is not None:
            return row[0]
        return None
    
    def setCorrespondentKey(self, emailAddress, key):
        emailAddress = emailAddress.lower()
        cursor = self.conn.cursor()
        if not self.correspondentExists(emailAddress):
            cursor.execute("INSERT INTO correspondents (email_address, key, red_herring_sent) VALUES(?, ?, ?)", (emailAddress, key, -1))
            logging.debug("EmailSecChal: db: Added a new correspondent key in the DB for %s" % emailAddress)
        else:
            cursor.execute("UPDATE correspondents SET key = ?, red_herring_sent = -1 WHERE email_address = ?", (key, emailAddress))
            logging.debug("EmailSecChal: db: Updated the correspondent key in the DB for %s" % emailAddress)

    def isRedHerringSent(self, emailAddress):
        emailAddress = emailAddress.lower()
        cursor = self.conn.cursor()
        cursor.execute("SELECT red_herring_sent FROM correspondents WHERE email_address = ?", (emailAddress, ))
        row = cursor.fetchone()
        if row is not None:
            return row[0] >= 0
        return False
    
    def redHerringSent(self, emailAddress):
        emailAddress = emailAddress.lower()
        cursor = self.conn.cursor()
        if not self.correspondentExists(emailAddress):
            cursor.execute("INSERT INTO correspondents (email_address, red_herring_sent) VALUES(?, ?)", (emailAddress, self.getCurrentTimestamp()))
        else:
            cursor.execute("UPDATE correspondents SET red_herring_sent = ? WHERE email_address = ?", (self.getCurrentTimestamp(), emailAddress))
        logging.debug("EmailSecChal: db: Set red herring as sent in DB for %s" % emailAddress)
        
    def getCurrentTimestamp(self):
        return int(time.time())
