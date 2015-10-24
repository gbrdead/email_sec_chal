import sqlite3
import shutil
import os
import gpgmime
import email.utils
import tempfile


class PgpException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class Pgp:
    
    configDir = "/data/email_sec_cache"
    dataDir = "/data/email_sec_cache"
    tempDir = "/tmp/email_sec_cache"

    initialized = False        
    keyServer = None
    botKeys = None
    dbConn = None

    emailAddress = None
    gnupgHomeDir = None
    gpg = None
    correspondentKey = None
    correspondentFingerprints = None
        
    
    @staticmethod
    def staticInit():
        if Pgp.initialized:
            return
        
        if not os.access(Pgp.dataDir, os.F_OK):
            os.makedirs(Pgp.dataDir)
        if not os.access(Pgp.tempDir, os.F_OK):
            os.makedirs(Pgp.tempDir)

        with open(os.path.join(Pgp.configDir, "bot.asc"), "r") as botKeysFile:
            Pgp.botKeys = botKeysFile.read()

        Pgp.dbConn = sqlite3.connect(os.path.join(Pgp.dataDir, "email_sec_cache.sqlite3"), isolation_level=None)
        cursor = Pgp.dbConn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS correspondents (email_address TEXT PRIMARY KEY, key TEXT)")
        
        Pgp.initialized = True
    
    def __init__(self, emailAddress, gpgVerbose = False):
        Pgp.staticInit()
        
        self.emailAddress = emailAddress
        
        self.gnupgHomeDir = tempfile.mkdtemp(dir = Pgp.tempDir, prefix = self.emailAddress + "_")
        self.gpg = gpgmime.GPG(gnupghome = self.gnupgHomeDir, verbose = gpgVerbose)
        
        self.gpg.import_keys(Pgp.botKeys)
        self.loadCorrespondentKeyFromDb()
    
    def __enter__(self):
        pass
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        shutil.rmtree(self.gnupgHomeDir, ignore_errors=True)
        
    def loadCorrespondentKeyFromDb(self):
        cursor = Pgp.dbConn.cursor()
        for row in cursor.execute('SELECT key FROM correspondents WHERE email_address = ?', (self.emailAddress, )):
            self.correspondentKey = row[0]
        self.importPublicKey()
        
    def loadCorrespondentKey(self, correspondentKey_):
        tmpFile = tempfile.NamedTemporaryFile(dir = Pgp.tempDir, delete=False, mode="w")
        tmpFileName = getattr(tmpFile, "name")
        tmpFile.write(correspondentKey_)
        tmpFile.close()
        keys = self.gpg.scan_keys(tmpFileName)
        os.remove(tmpFileName)
        
        expectedUid = ("<" + self.emailAddress + ">").lower()
        suitable = False
        for key in keys:
            for uid in key["uids"]:
                if uid.lower().endswith(expectedUid):
                    suitable = True
                    break
            if suitable:
                break
        if not suitable:
            raise PgpException("No correspondent key for email address %s found." % self.emailAddress)
        
        self.correspondentKey = correspondentKey_
        self.saveCorrespondentKeyToDb()
        self.importPublicKey()
        
    def saveCorrespondentKeyToDb(self):
        cursor = Pgp.dbConn.cursor()
        if self.correspondentKey is not None:
            cursor.execute("SELECT key FROM correspondents WHERE email_address = ?", (self.emailAddress, ))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO correspondents (email_address, key) VALUES(?, ?)", (self.emailAddress, self.correspondentKey))
            else:
                cursor.execute("UPDATE correspondents SET key = ? WHERE email_address = ?", (self.correspondentKey, self.emailAddress))
        else:
            cursor.execute("DELETE FROM correspondents WHERE email_address = ?", (self.emailAddress))
            
    def importPublicKey(self):
        if self.correspondentFingerprints is not None:
            self.gpg.delete_keys(self.correspondentFingerprints)
            self.correspondentFingerprints = None
        if self.correspondentKey is not None:
            importResult = self.gpg.import_keys(self.correspondentKey)
            self.correspondentFingerprints = importResult.fingerprints
            
    def parseMessage(self, msg):
        _, emailAddress = email.utils.parseaddr(msg["From"])
        if not emailAddress:
            raise PgpException("Missing From header in message: %s" % msg)
        if emailAddress != self.emailAddress:
            raise PgpException("Wrong sender: %s (expected %s)" % (emailAddress, self.emailAddress))
        
        isEncrypted = gpgmime.is_encrypted(msg) 
        if isEncrypted:
            msg, status = self.gpg.decrypt_email(msg)
            if not status:
                raise PgpException(status.stderr)
            isVerified = status.valid
        else:
            isSigned = gpgmime.is_signed(msg)
            if isSigned:
                msg, status = self.gpg.verify_email(msg) 
                isVerified = status.valid 
            else:
                isVerified = False
                
        return isEncrypted, isVerified, msg
