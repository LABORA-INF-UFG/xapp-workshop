# Imports from local files
from .custom_xapp import XappRmrSubAct

def launchXapp():
    """
    Entrypoint called in the xApp Dockerfile.
    """
    xapp_instance = XappRmrSubAct() # Instantiating our custom xApp 
    xapp_instance.start() # Starting our custom xApp in threaded mode

if __name__ == "__main__":
    launchXapp()