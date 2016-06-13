# -*- coding: utf-8 -*-
import logging
import email_sec_cache
import configparser
import sys


configFile = "/data/email_sec_cache/email_sec_cache.ini"
resourceDir = None
dataDir = None
tempDir = None

geocacheNames = set()
logLevel = logging.NOTSET
keyUploadServerPort = -1
smtpServerHost = None


def loadConfiguration():
    config = configparser.ConfigParser()
    config.read(email_sec_cache.configFile)
    
    email_sec_cache.geocacheNames = set(map(str.upper, email_sec_cache.util.extractWords(config["misc"]["geocache_names"])))
    email_sec_cache.logLevel = logging._nameToLevel[config["misc"]["log_level"].upper()]
    email_sec_cache.keyUploadServerPort = int(config["misc"]["key_upload_server_port"])
    email_sec_cache.smtpServerHost = config["misc"]["smtp_server_host"]
    email_sec_cache.resourceDir = config["dirs"]["resource_dir"]
    email_sec_cache.dataDir = config["dirs"]["data_dir"]
    email_sec_cache.tempDir = config["dirs"]["temp_dir"]
    
    logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=email_sec_cache.logLevel)
    
    logging.info("EmailSecCache: main: Geocache names: %s" % ", ".join(email_sec_cache.geocacheNames))
    logging.info("EmailSecCache: main: Log level: %s" % logging.getLevelName(email_sec_cache.logLevel))
    logging.info("EmailSecCache: main: Key upload server port: %d" % email_sec_cache.keyUploadServerPort)
    logging.info("EmailSecCache: main: SMTP server host: %s" % email_sec_cache.smtpServerHost)
    logging.info("EmailSecCache: main: Resource directory: %s" % email_sec_cache.resourceDir)
    logging.info("EmailSecCache: main: Data directory: %s" % email_sec_cache.dataDir)
    logging.info("EmailSecCache: main: Temporary directory: %s" % email_sec_cache.tempDir)


if __name__ == "__main__":
    try:
        loadConfiguration()
    except:
        logging.exception("EmailSecCache: main: Cannot read configuration")
        sys.exit(1)

    try:
        email_sec_cache.startKeyUploadServer()
    except:
        logging.exception("EmailSecCache: main: Cannot start the key upload server")
        sys.exit(2)
        
    try:
        mailBot = email_sec_cache.MailBot()
        mailBot.run()
    except:
        logging.exception("EmailSecCache: main: The mailbot stopped with an exception")
        sys.exit(3)
