# Template: copy this file to user_config.py and fill in YOUR machine's values.
# user_config.py is git-ignored so each user keeps their own config.
from pynetdicom import AE

class UserConfig:
    IP = "192.168.x.x"          # IP of the machine running the scripts (receives the images)
    PORT = 106                  # port Telemis sends to
    CALLING_AET = "RMN-XXXX"    # your AE title, declared in Telemis with IP + PORT

    CALLED_AET = "TELEMISQR"
