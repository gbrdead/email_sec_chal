# -*- coding: utf-8 -*-
import logging
import email_sec_cache
import configparser
import sys


configFile = "/data/email_sec_cache/email_sec_cache.ini"
resourceDir = None
dataDir = None
tempDir = None

geocacheName = None
logLevel = logging.NOTSET
keyUploadServerPort = -1


def loadConfiguration():
    config = configparser.ConfigParser()
    config.read(configFile)
    
    email_sec_cache.geocacheName = config["misc"]["geocache_name"]
    
    logLevelAsString = config["misc"]["log_level"].upper()
    if logLevelAsString == "DEBUG":
        email_sec_cache.logLevel = logging.DEBUG
    elif logLevelAsString == "INFO":
        email_sec_cache.logLevel = logging.INFO
    elif logLevelAsString == "WARN" or logLevelAsString == "WARNING":
        email_sec_cache.logLevel = logging.WARN
    elif logLevelAsString == "ERROR":
        email_sec_cache.logLevel = logging.ERROR
    elif logLevelAsString == "CRITICAL":
        email_sec_cache.logLevel = logging.CRITICAL

    email_sec_cache.keyUploadServerPort = int(config["misc"]["key_upload_server_port"])
    
    email_sec_cache.resourceDir = config["dirs"]["resource_dir"]
    email_sec_cache.dataDir = config["dirs"]["data_dir"]
    email_sec_cache.tempDir = config["dirs"]["temp_dir"]


if __name__ == "__main__":
    try:
        loadConfiguration()
    except:
        logging.exception("Cannot read configuration")
        sys.exit(1)
    
    logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=email_sec_cache.logLevel)

    try:
        email_sec_cache.startKeyUploadServer()
    except:
        logging.exception("Cannot start the key upload server")
        sys.exit(2)
        
    try:
        mailBot = email_sec_cache.MailBot()
        mailBot.run()
    except:
        logging.exception("Mailbot stopped with an exception")
        sys.exit(3)
