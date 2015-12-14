# -*- coding: utf-8 -*-
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
    botFrom = None

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

        officialBotKeysFilePath = os.path.join(email_sec_cache.configDir, email_sec_cache.officialBotKeysFileName)
        with open(officialBotKeysFilePath, "r") as officialBotKeysFile:
            Pgp.officialBotKeys = officialBotKeysFile.read()
            
        impostorBotKeysFilePath = os.path.join(email_sec_cache.configDir, email_sec_cache.impostorBotKeysFileName)
        with open(impostorBotKeysFilePath, "r") as impostorBotKeysFile:
            Pgp.impostorBotKeys = impostorBotKeysFile.read()
            
        Pgp.botFrom = Pgp.getBotFromHeaderValue(Pgp.officialBotKeys)

        logging.debug(u"EmailSecCache: Pgp static initialization successful")
        Pgp.initialized = True
    
    @staticmethod    
    def getBotFromHeaderValue(botKeys):
        gnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        gpg = gpgmime.GPG(gnupghome = gnupgHomeDir, verbose=logging.getLogger().isEnabledFor(logging.DEBUG))
        gpg.import_keys(botKeys)
        botFrom = gpg.list_keys(secret = True)[0]["uids"][0] 
        shutil.rmtree(gnupgHomeDir, ignore_errors=True)
        logging.info(u"EmailSecCache: The value for the bot From header is: " + botFrom)
        return botFrom
    
    
    def __init__(self, emailAddress):
        Pgp.staticInit()
        
        self.db = email_sec_cache.Db()
        self.emailAddress = emailAddress
        logging.debug(u"EmailSecCache: Creating a Pgp instance for %s" % self.emailAddress)
        
        self.officialGnupgHomeDir, self.officialGpg = self.initBotGpg(u"official", Pgp.officialBotKeys)
        self.impostorGnupgHomeDir, self.impostorGpg = self.initBotGpg(u"impostor", Pgp.impostorBotKeys)
        self.loadCorrespondentKeyFromDb()
    
    def initBotGpg(self, botName, botKeys):
        gnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir, prefix = self.emailAddress + "_" + botName + "_")
        gpg = gpgmime.GPG(gnupghome = gnupgHomeDir)
        gpg.import_keys(botKeys)
        logging.debug(u"EmailSecCache: Created a GPG home directory in %s" % gnupgHomeDir)
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
        logging.debug(u"EmailSecCache: Deleted the GPG home directory %s" % gnupgHomeDir)
        
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
            logging.warning(u"EmailSecCache: No correspondent key in DB for %s" % self.emailAddress)
            
        msgId = email_sec_cache.getHeaderAsUnicode(msg, "Message-ID")
        
        from_ = email_sec_cache.getHeaderAsUnicode(msg, "From")
        _, emailAddress = email.utils.parseaddr(from_) 
        if not emailAddress:
            raise PgpException(u"Missing From header (%s)" % msgId)
        if emailAddress != self.emailAddress:
            raise PgpException(u"Wrong sender: %s (expected %s) (%s)" % (emailAddress, self.emailAddress, msgId))
        
        isForImpostor = False
        isEncrypted = gpgmime.is_encrypted(msg)
        if isEncrypted:
            logging.debug(u"EmailSecCache: The message with ID %s is encrypted" % msgId)
            saveMsg = msg
            msg, status = self.officialGpg.decrypt_email(msg)
            if status:
                logging.debug(u"EmailSecCache: The message with ID %s was decrypted by the official bot's key" % msgId)
            else:
                saveError = status.stderr
                msg = saveMsg
                msg, status = self.impostorGpg.decrypt_email(msg)
                if not status:
                    raise PgpException(saveError)
                logging.debug(u"EmailSecCache: The message with ID %s was decrypted by the impostor bot's key" % msgId)
                isForImpostor = True
            isVerified = status.valid
        else:
            logging.debug(u"EmailSecCache: The message with ID %s is not encrypted" % msgId)
            isSigned = gpgmime.is_signed(msg)
            if isSigned:
                logging.debug(u"EmailSecCache: The message with ID %s is signed" % msgId)
                msg, status = self.officialGpg.verify_email(msg) 
                isVerified = status.valid
            else:
                logging.debug(u"EmailSecCache: The message with ID %s is not signed" % msgId)
                isVerified = False
                
        if isVerified:
            logging.debug(u"EmailSecCache: The message with ID %s has a valid signature" % msgId)
        else:
            logging.debug(u"EmailSecCache: The message with ID %s has an invalid signature" % msgId)
                
        return isEncrypted, isVerified, msg, isForImpostor
