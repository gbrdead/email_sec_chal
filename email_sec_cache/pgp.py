# -*- coding: utf-8 -*-
import shutil
import os
import tempfile
import email_sec_cache
import logging
import io
import email.generator
import gnupg
import email.mime.multipart
import email.mime.application
import email.encoders



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
    officialFingerprints = None
    impostorFingerprints = None
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

        logging.debug("EmailSecCache: Pgp static initialization successful")
        Pgp.initialized = True
        
    @staticmethod
    def createGpg(gnupgHomeDir):
        return gnupg.GPG(gnupghome = gnupgHomeDir, verbose=logging.getLogger().isEnabledFor(logging.DEBUG))
    
    @staticmethod    
    def getBotFromHeaderValue(botKeys):
        gnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        gpg = Pgp.createGpg(gnupgHomeDir)
        gpg.import_keys(botKeys)
        botFrom = gpg.list_keys(secret = True)[0]["uids"][0] 
        shutil.rmtree(gnupgHomeDir, ignore_errors=True)
        logging.info("EmailSecCache: The value for the bot From header is: " + botFrom)
        return botFrom
    
    
    def __init__(self, emailAddress):
        Pgp.staticInit()
        
        self.db = email_sec_cache.Db()
        self.emailAddress = emailAddress
        logging.debug("EmailSecCache: Creating a Pgp instance for %s" % self.emailAddress)
        
        self.officialGnupgHomeDir, self.officialGpg, self.officialFingerprints = self.initBotGpg("official", Pgp.officialBotKeys)
        self.impostorGnupgHomeDir, self.impostorGpg, self.impostorFingerprints = self.initBotGpg("impostor", Pgp.impostorBotKeys)
        self.loadCorrespondentKeyFromDb()
    
    def initBotGpg(self, botName, botKeys):
        gnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir, prefix = self.emailAddress + "_" + botName + "_")
        gpg = Pgp.createGpg(gnupgHomeDir)
        gpg.encoding = "utf-8"
        importResult = gpg.import_keys(botKeys)
        logging.debug("EmailSecCache: Created a GPG home directory in %s" % gnupgHomeDir)
        return gnupgHomeDir, gpg, importResult.fingerprints

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def close(self):
        self.removeGnupgHomeDir(self.officialGnupgHomeDir)
        self.removeGnupgHomeDir(self.impostorGnupgHomeDir)
        
    def removeGnupgHomeDir(self, gnupgHomeDir):
        try:
            shutil.rmtree(gnupgHomeDir)
            logging.debug("EmailSecCache: Deleted the GPG home directory %s" % gnupgHomeDir)
        except:
            logging.warning("EmailSecCache: Cannot remove directory %s" % gnupgHomeDir, exc_info=True)

        
    def loadCorrespondentKeyFromDb(self):
        self.correspondentKey = self.db.getCorrespondentKey(self.emailAddress)
        if self.correspondentKey is None:
            logging.warning("EmailSecCache: No correspondent key in DB for %s" % self.emailAddress)
        self.importPublicKey()
        
    def loadCorrespondentKey(self, correspondentKey_):
        tmpFile = tempfile.NamedTemporaryFile(dir = email_sec_cache.tempDir, delete=False, mode="w")
        tmpFile.write(correspondentKey_)
        tmpFile.close()
        keys = self.officialGpg.scan_keys(tmpFile.name)
        email_sec_cache.removeFile(tmpFile.name)
        
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
            raise email_sec_cache.PgpException("No correspondent key for email address %s found." % self.emailAddress)
        
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
            

    def verifyMessageWithDetachedSignature(self, msg, signature):
        binaryData = self.convertToBinary(msg)
        
        signatureFile = tempfile.NamedTemporaryFile(dir = email_sec_cache.tempDir, delete=False, mode="w")
        signatureFile.write(signature)
        signatureFile.close()
        logging.debug("EmailSecCache: Wrote detached signature to temporary file %s" % signatureFile.name)
        
        verified = self.officialGpg.verify_data(signatureFile.name, binaryData)
        email_sec_cache.removeFile(signatureFile.name)
        return verified

    def signAndEncrypt(self, msg, asImpostor):
        binaryData = self.convertToBinary(msg)
        if asImpostor:
            recipients = self.correspondentFingerprints + self.impostorFingerprints
            encryptedData = self.impostorGpg.encrypt(binaryData, recipients, sign=self.impostorFingerprints[0], always_trust=True)
        else:
            recipients = self.correspondentFingerprints + self.officialFingerprints
            encryptedData = self.officialGpg.encrypt(binaryData, recipients, sign=self.officialFingerprints[0], always_trust=True)
        
        encryptedMsg = email.mime.multipart.MIMEMultipart("encrypted", protocol="application/pgp-encrypted")
        
        pgpIdentification = email.mime.application.MIMEApplication("Version: 1\n", "pgp-encrypted", email.encoders.encode_7or8bit)
        del pgpIdentification["MIME-Version"]
        encryptedMsg.attach(pgpIdentification)
        
        encryptedAsc = email.mime.application.MIMEApplication(str(encryptedData), "octet-stream", email.encoders.encode_7or8bit)
        del encryptedAsc["MIME-Version"]
        encryptedMsg.attach(encryptedAsc)
        
        return encryptedMsg

    def convertToBinary(self, msg):
        buf = io.BytesIO()
        generator = email.generator.BytesGenerator(buf, maxheaderlen=0)
        generator.flatten(msg)
        return buf.getvalue()
