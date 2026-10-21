# Template: copy this file to server_config.py and set YOUR calling AE title.
# server_config.py is git-ignored so each user keeps their own config.
from pynetdicom import AE

class TelemisConfig:
    # Telemis server (AIM)
    HOST = "192.168.0.170"
    PORT = 106
    CALLED_AET = "TELEMISQR"

    CALLING_AET = "RMN-XXXX"    # your AE title, declared in Telemis
