import os
import sqlite3
import shutil
import cme
from cme.helpers.logger import highlight
#from cme.helpers.powershell import is_powershell_installed
from cme.loaders.protocol_loader import protocol_loader
from subprocess import check_output, PIPE
from sys import exit

CME_PATH  = os.path.expanduser('~/.cme')
TMP_PATH  = os.path.join('/tmp', 'cme_hosted')
WS_PATH   = os.path.join(CME_PATH, 'workspaces')
CERT_PATH = os.path.join(CME_PATH, 'cme.pem')
CONFIG_PATH = os.path.join(CME_PATH, 'cme.conf')

def first_run_setup(logger):

    if not os.path.exists(TMP_PATH):
        os.mkdir(TMP_PATH)

    if not os.path.exists(CME_PATH):
        logger.info('First time use detected')
        logger.info('Creating home directory structure')
        os.mkdir(CME_PATH)

    folders = ['logs', 'modules', 'protocols', 'workspaces', 'obfuscated_scripts']
    for folder in folders:
        if not os.path.exists(os.path.join(CME_PATH, folder)):
            os.mkdir(os.path.join(CME_PATH,folder))

    if not os.path.exists(os.path.join(WS_PATH, 'default')):
        logger.info('Creating default workspace')
        os.mkdir(os.path.join(WS_PATH, 'default'))

    p_loader =  protocol_loader()
    protocols = p_loader.get_protocols()
    for protocol in protocols.keys():
        try:
            protocol_object = p_loader.load_protocol(protocols[protocol]['dbpath'])
        except KeyError:
            continue

        proto_db_path = os.path.join(WS_PATH, 'default', protocol + '.db')

        if not os.path.exists(proto_db_path):
            logger.info('Initializing {} protocol database'.format(protocol.upper()))
            conn = sqlite3.connect(proto_db_path)
            c = conn.cursor()

            # try to prevent some of the weird sqlite I/O errors
            c.execute('PRAGMA journal_mode = OFF')
            c.execute('PRAGMA foreign_keys = 1')

            getattr(protocol_object, 'database').db_schema(c)

            # commit the changes and close everything off
            conn.commit()
            conn.close()

    if not os.path.exists(CONFIG_PATH):
        logger.info('Copying default configuration file')
        default_path = os.path.join(os.path.dirname(cme.__file__), 'data', 'cme.conf')
        shutil.copy(default_path, CME_PATH)

    if not os.path.exists(CERT_PATH):
        logger.info('Generating SSL certificate')
        try:
            out = check_output(['openssl', 'help'], stderr=PIPE)
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                logger.error('OpenSSL command line utility is not installed, could not generate certificate')
                exit(1)
            else:
                logger.error('Error while generating SSL certificate: {}'.format(e))
                exit(1)

        os.system('openssl req -new -x509 -keyout {path} -out {path} -days 365 -nodes -subj "/C=US" > /dev/null 2>&1'.format(path=CERT_PATH))

    #if not is_powershell_installed(): logger.error(highlight('[!] PowerShell not found and/or not installed, advanced PowerShell script obfuscation will be disabled!'))