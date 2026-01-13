from pynetdicom import AE

class TelemisConfig:
    # HOST = "10.2.30.172"
    # HOST = "10.2.30.172"
    HOST = "192.168.0.170"

    # PORT = 7008
    PORT= 106
    # CALLING_AET = "RMN-STATION"
    CALLING_AET = "RMN-TEST"
    CALLED_AET = "TELEMISQR"
    # Timeouts (in seconds)
    # DIMSE_TIMEOUT: timeout for DIMSE operations (C-STORE, C-FIND, C-GET, etc.)
    # ACSE_TIMEOUT: timeout for association (ACSE) establishment
    # Increase DIMSE_TIMEOUT if transfers are slow or the server is slow to respond.
    # DIMSE_TIMEOUT = 600
    # ACSE_TIMEOUT = 600   
    # NETWORK_TIMEOUT = 600
