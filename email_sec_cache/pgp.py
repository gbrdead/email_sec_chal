import shutil
import os
import gpgmime
import email.utils
import tempfile
import email_sec_cache
import logging


class PgpException(email_sec_cache.EmailSecCacheException):
    pass


class Pgp:
    
    initialized = False
    officialBotKeys = None
    impostorBotKeys = None

    db = None
    emailAddress = None
    officialGnupgHomeDir = None
    impostorGnupgHomeDir = None
    officialGpg = None
    impostorGpg = None
    correspondentKey = None
    correspondentFingerprints = None
        
    
    @staticmethod
    def staticInit():
        if Pgp.initialized:
            return
        
        if not os.access(email_sec_cache.tempDir, os.F_OK):
            os.makedirs(email_sec_cache.tempDir)

        with open(os.path.join(email_sec_cache.configDir, u"officialBot.asc"), "r") as botKeysFile:
            Pgp.officialBotKeys = botKeysFile.read()

        with open(os.path.join(email_sec_cache.configDir, u"impostorBot.asc"), "r") as impostorBotKeysFile:
            Pgp.impostorBotKeys = impostorBotKeysFile.read()

        logging.debug(u"Pgp static initialization successful")
        Pgp.initialized = True
    
    def __init__(self, emailAddress, gpgVerbose = False):
        Pgp.staticInit()
        
        self.db = email_sec_cache.Db()
        self.emailAddress = emailAddress
        logging.debug(u"Creating a Pgp instance for %s" % self.emailAddress)
        
        self.officialGnupgHomeDir, self.officialGpg = self.initBotGpg(u"official", Pgp.officialBotKeys, gpgVerbose)
        self.impostorGnupgHomeDir, self.impostorGpg = self.initBotGpg(u"impostor", Pgp.impostorBotKeys, gpgVerbose)
        self.loadCorrespondentKeyFromDb()
    
    def initBotGpg(self, botName, keys, gpgVerbose = False):
        gnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir, prefix = self.emailAddress + "_" + botName + "_")
        gpg = gpgmime.GPG(gnupghome = gnupgHomeDir, verbose = gpgVerbose)
        gpg.import_keys(keys)
        logging.debug(u"Created a GPG home directory in %s" % gnupgHomeDir)
        return gnupgHomeDir, gpg

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        self.removeGnupgHomeDir(self.officialGnupgHomeDir)
        self.removeGnupgHomeDir(self.impostorGnupgHomeDir)
        
    def removeGnupgHomeDir(self, gnupgHomeDir):
        shutil.rmtree(gnupgHomeDir, ignore_errors=True)
        logging.debug(u"Deleted the GPG home directory %s" % gnupgHomeDir)
        
    def loadCorrespondentKeyFromDb(self):
        self.correspondentKey = self.db.getCorrespondentKey(self.emailAddress)
        self.importPublicKey()
        
    def loadCorrespondentKey(self, correspondentKey_):
        tmpFile = tempfile.NamedTemporaryFile(dir = email_sec_cache.tempDir, delete=False, mode="w")
        tmpFileName = getattr(tmpFile, "name")
        tmpFile.write(correspondentKey_)
        tmpFile.close()
        keys = self.officialGpg.scan_keys(tmpFileName)
        os.remove(tmpFileName)
        
        expectedUid = (u"<" + self.emailAddress + u">").lower()
        suitable = False
        for key in keys:
            for uid in key["uids"]:
                if uid.lower().endswith(expectedUid):
                    suitable = True
                    break
            if suitable:
                break
        if not suitable:
            raise PgpException(u"No correspondent key for email address %s found." % self.emailAddress)
        
        self.correspondentKey = correspondentKey_
        self.db.setCorrespondentKey(self.emailAddress, self.correspondentKey)
        self.importPublicKey()
        
    def importPublicKey(self):
        if self.correspondentFingerprints is not None:
            self.officialGpg.delete_keys(self.correspondentFingerprints)
            self.impostorGpg.delete_keys(self.correspondentFingerprints)
            self.correspondentFingerprints = None
        if self.correspondentKey is not None:
            importResult = self.officialGpg.import_keys(self.correspondentKey)
            self.correspondentFingerprints = importResult.fingerprints
            self.impostorGpg.import_keys(self.correspondentKey)
            
    def parseMessage(self, msg):
        if self.correspondentKey is None:
            logging.warning(u"No correspondent key in DB for %s" % self.emailAddress)
        
        from_ = email_sec_cache.getHeaderAsUnicode(msg, "From")
        _, emailAddress = email.utils.parseaddr(from_) 
        if not emailAddress:
            raise PgpException(u"Missing From header")
        if emailAddress != self.emailAddress:
            raise PgpException(u"Wrong sender: %s (expected %s)" % (emailAddress, self.emailAddress))
        
        isForImpostor = False
        isEncrypted = gpgmime.is_encrypted(msg) 
        if isEncrypted:
            saveMsg = msg
            msg, status = self.officialGpg.decrypt_email(msg)
            if not status:
                saveError = status.stderr
                msg = saveMsg
                msg, status = self.impostorGpg.decrypt_email(msg)
                if not status:
                    raise PgpException(saveError)
                isForImpostor = True
            isVerified = status.valid
        else:
            isSigned = gpgmime.is_signed(msg)
            if isSigned:
                msg, status = self.officialGpg.verify_email(msg) 
                isVerified = status.valid 
            else:
                isVerified = False
                
        return isEncrypted, isVerified, msg, isForImpostor
