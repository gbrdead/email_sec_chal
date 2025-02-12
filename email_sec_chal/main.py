# -*- coding: utf-8 -*-
import logging
import email_sec_chal
import configparser
import sys


configFile = "email_sec_chal.ini"
resourceDir = None
dataDir = None
tempDir = None

triggerWords = set()
logLevel = logging.NOTSET
keyUploadServerPort = -1
smtpServerHost = None
silentPeriodSec = 0


def loadConfiguration():
    config = configparser.ConfigParser()
    config.read(email_sec_chal.configFile)
    
    email_sec_chal.triggerWords = set(map(str.upper, email_sec_chal.util.extractWords(config["misc"]["trigger_words"])))
    email_sec_chal.logLevel = logging._nameToLevel[config["misc"]["log_level"].upper()]
    email_sec_chal.keyUploadServerPort = int(config["misc"]["key_upload_server_port"])
    email_sec_chal.smtpServerHost = config["misc"]["smtp_server_host"]
    email_sec_chal.silentPeriodSec = int(config["misc"]["silent_period_sec"])
    email_sec_chal.resourceDir = config["dirs"]["resource_dir"]
    email_sec_chal.dataDir = config["dirs"]["data_dir"]
    email_sec_chal.tempDir = config["dirs"]["temp_dir"]
    
    logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S", level=email_sec_chal.logLevel)
    
    logging.info("EmailSecChal: main: Trigger words: %s" % ", ".join(email_sec_chal.triggerWords))
    logging.info("EmailSecChal: main: Log level: %s" % logging.getLevelName(email_sec_chal.logLevel))
    logging.info("EmailSecChal: main: Key upload server port: %d" % email_sec_chal.keyUploadServerPort)
    logging.info("EmailSecChal: main: SMTP server host: %s" % email_sec_chal.smtpServerHost)
    logging.info("EmailSecChal: main: Resource directory: %s" % email_sec_chal.resourceDir)
    logging.info("EmailSecChal: main: Data directory: %s" % email_sec_chal.dataDir)
    logging.info("EmailSecChal: main: Temporary directory: %s" % email_sec_chal.tempDir)


def main():
    if len(sys.argv) > 1:
        email_sec_chal.configFile = sys.argv[1]
    
    try:
        loadConfiguration()
    except:
        logging.exception("EmailSecChal: main: Cannot read configuration")
        sys.exit(1)

    try:
        email_sec_chal.startKeyUploadServer()
    except:
        logging.exception("EmailSecChal: main: Cannot start the key upload server")
        sys.exit(2)
        
    try:
        mailBot = email_sec_chal.MailBot()
        mailBot.run()
    except:
        logging.exception("EmailSecChal: main: The mailbot stopped with an exception")
        sys.exit(3)

if __name__ == "__main__":
    main()
