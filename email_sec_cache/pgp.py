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
import email.utils



class Pgp:
    
    initialized = False
    officialBotKeys = None
    impostorBotKeys = None
    botFrom = None
    botEmailAddress = None
    officialBotKeysFilePath = None

    db = None
    emailAddress = None
    officialGnupgHomeDir = None
    impostorGnupgHomeDir = None
    officialGpg = None
    impostorGpg = None
    officialFingerprints = []
    impostorFingerprints = []
    correspondentKey = None
    correspondentFingerprints = []
        
    
    @staticmethod
    def staticInit():
        if Pgp.initialized:
            return
        
        if not os.access(email_sec_cache.tempDir, os.F_OK):
            os.makedirs(email_sec_cache.tempDir)

        Pgp.officialBotKeysFilePath = os.path.join(email_sec_cache.resourceDir, "officialBot.asc")
        with open(Pgp.officialBotKeysFilePath, "r") as officialBotKeysFile:
            Pgp.officialBotKeys = officialBotKeysFile.read()
            
        impostorBotKeysFilePath = os.path.join(email_sec_cache.resourceDir, "impostorBot.asc")
        with open(impostorBotKeysFilePath, "r") as impostorBotKeysFile:
            Pgp.impostorBotKeys = impostorBotKeysFile.read()
            
        Pgp.botFrom = Pgp.getBotFromHeaderValue()
        _, Pgp.botEmailAddress = email.utils.parseaddr(Pgp.botFrom)
        Pgp.botEmailAddress = Pgp.botEmailAddress.lower()

        logging.debug("EmailSecCache: pgp: Static initialization successful")
        Pgp.initialized = True
        
    @staticmethod
    def createGpg(gnupgHomeDir):
        return gnupg.GPG(gnupghome = gnupgHomeDir, verbose=logging.getLogger().isEnabledFor(logging.DEBUG))
    
    @staticmethod
    def createTempGpg():
        gnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir)
        gpg = Pgp.createGpg(gnupgHomeDir)
        return gpg, gnupgHomeDir
    
    @staticmethod    
    def getBotFromHeaderValue():
        gpg, gnupgHomeDir = Pgp.createTempGpg()
        try:
            gpg.import_keys(Pgp.officialBotKeys)
            botFrom = gpg.list_keys(secret = True)[0]["uids"][0]
        finally:
            shutil.rmtree(gnupgHomeDir, ignore_errors=True)
        
        logging.info("EmailSecCache: pgp: The value for the bot's From header is: " + botFrom)
        return botFrom

    @staticmethod    
    def storeCorrespondentKey(correspondentKey):
        gpg, gnupgHomeDir = Pgp.createTempGpg()
        try:
            tmpFile = tempfile.NamedTemporaryFile(dir = email_sec_cache.tempDir, delete=False, mode="w")
            try:
                tmpFile.write(correspondentKey)
                tmpFile.close()
                keys = gpg.scan_keys(tmpFile.name)
            finally:
                email_sec_cache.removeFile(tmpFile.name)
        finally:
            shutil.rmtree(gnupgHomeDir, ignore_errors=True)
            
        emailAddresses = []
        db = email_sec_cache.Db()
        for key in keys:
            for uid in key["uids"]:
                _, emailAddress = email.utils.parseaddr(uid)
                if emailAddress is not None:
                    emailAddress = emailAddress.lower()
                    emailAddresses.append(emailAddress)
                    db.setCorrespondentKey(emailAddress, correspondentKey)
                
        logging.info("EmailSecCache: pgp: Imported keys for the following addresses: %s" % (", ".join(emailAddresses)))
        return emailAddresses
    
    def __init__(self, emailAddress_=""):
        Pgp.staticInit()
        
        self.db = email_sec_cache.Db()
        self.emailAddress = emailAddress_
        logging.debug("EmailSecCache: pgp: Creating an instance for %s" % (self.emailAddress if self.emailAddress is not None else "nobody"))
        if self.emailAddress is not None:
            self.emailAddress = self.emailAddress.lower()
        
        self.officialGnupgHomeDir, self.officialGpg, self.officialFingerprints = self.initBotGpg("official", Pgp.officialBotKeys)
        self.impostorGnupgHomeDir, self.impostorGpg, self.impostorFingerprints = self.initBotGpg("impostor", Pgp.impostorBotKeys)
        if self.emailAddress:
            self.loadCorrespondentKeyFromDb()
    
    def initBotGpg(self, botName, botKeys):
        gnupgHomeDir = tempfile.mkdtemp(dir = email_sec_cache.tempDir, prefix = self.emailAddress + "_" + botName + "_")
        gpg = Pgp.createGpg(gnupgHomeDir)
        gpg.encoding = "utf-8"
        importResult = gpg.import_keys(botKeys)
        logging.debug("EmailSecCache: pgp: Created a GPG home directory in %s" % gnupgHomeDir)
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
            logging.debug("EmailSecCache: pgp: Deleted the GPG home directory %s" % gnupgHomeDir)
        except:
            logging.warning("EmailSecCache: pgp: Cannot remove directory %s" % gnupgHomeDir, exc_info=True)

        
    def loadCorrespondentKeyFromDb(self):
        self.correspondentKey = self.db.getCorrespondentKey(self.emailAddress)
        if self.correspondentKey is None:
            logging.warning("EmailSecCache: pgp: No correspondent key in DB for %s" % self.emailAddress)
        else:
            importResult = self.officialGpg.import_keys(self.correspondentKey)
            self.correspondentFingerprints = importResult.fingerprints
            self.impostorGpg.import_keys(self.correspondentKey)
            
    def getBotPublicKey(self, fingerprints, gpg, botName):
        for fingerprint in fingerprints:
            publicKey = gpg.export_keys(fingerprint)
            if publicKey:
                return publicKey
        raise email_sec_cache.PgpException("The public key of the %s bot could not be exported." % botName)
    
    def getOfficialPublicKey(self):
        return self.getBotPublicKey(self.officialFingerprints, self.officialGpg, "official")

    def getImpostorPublicKey(self):
        return self.getBotPublicKey(self.impostorFingerprints, self.impostorGpg, "impostor")
            

    def verifyMessageWithDetachedSignature(self, msg, signature):
        binaryData = self.convertToBinary(msg)
        
        signatureFile = tempfile.NamedTemporaryFile(dir = email_sec_cache.tempDir, delete=False, mode="w")
        signatureFile.write(signature)
        signatureFile.close()
        logging.debug("EmailSecCache: pgp: Wrote detached signature to temporary file %s" % signatureFile.name)
        
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
        email_sec_cache.removeMimeVersion(pgpIdentification)
        encryptedMsg.attach(pgpIdentification)
        
        encryptedAsc = email.mime.application.MIMEApplication(str(encryptedData), "octet-stream", email.encoders.encode_7or8bit)
        email_sec_cache.removeMimeVersion(encryptedAsc)
        email_sec_cache.setMimeAttachmentFileName(encryptedAsc, "encrypted.asc")
        encryptedMsg.attach(encryptedAsc)
        
        return encryptedMsg

    def convertToBinary(self, msg):
        buf = io.BytesIO()
        generator = email.generator.BytesGenerator(buf, maxheaderlen=0)
        generator.flatten(msg, linesep="\r\n")
        return buf.getvalue()
