
# Imports from OSC libraries
from ricxappframe.xapp_frame import Xapp, rmr
from mdclogpy import Logger, Level

# Imports from other libraries
from time import sleep
from threading import Thread
import signal

class XappLogSdlRest:
    """
    Custom xApp class.

    Parameters
    ----------
    thread: bool = True
        Flag for executing the xApp loop as a thread. Default is True.
    """
    def __init__(self, thread:bool = True):
        """
        Initializes the custom xApp instance and instatiates the xApp framework object.
        """
        
        # Initializing a logger for the custom xApp instance in Debug level (logs everything)
        self.logger = Logger(name="XappLogSdlRest", level=Level.DEBUG) # The name is included in each log entry, Levels: DEBUG < INFO < WARNING < ERROR
        self.logger.get_env_params_values() # Getting the MDC key-value pairs from the environment
        self.logger.info("Initializing the xApp.")

        # Instatiating the xApp framework object 
        self._xapp = Xapp(entrypoint=self._entrypoint, # Custom entrypoint for starting the framework xApp object
                                 rmr_port=4560, # Port for RMR data
                                 rmr_wait_for_ready=True, # Block xApp initiation until RMR is ready
                                 use_fake_sdl=False) # Use a fake in-memory SDL

        # Registering a handler for terminating the xApp after TERMINATE, QUIT, or INTERRUPT signals
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGQUIT, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Initializing custom control variables
        self._shutdown = False # Stops the xApp loop if True
        self._thread = thread # True for executing the xApp loop as a thread
    
    def _entrypoint(self, xapp:Xapp):
        """
        Function containing the xApp logic. Called by the xApp framework object when it executes its run() method.
        
        Parameters
        ----------
        xapp: Xapp
            This is the xApp framework object (passed by the framework).
        """ 
        if self._thread:
            self.logger.info("Starting xApp loop in threaded mode.")
            Thread(target=self._loop).start()
        else:
            self.logger.info("Starting xApp loop in non-threaded mode.")
            self._loop()
        
    def _loop(self):
        """
        Loops logging an increasing counter each second.
        """
        i = 1 # How many times we looped
        while not self._shutdown: # True since custom xApp initialization until stop() is called
            self.logger.info("Looped {} times.".format(i))
            i+=1
            sleep(1) # Sleeps for 1 second

    def _handle_signal(self, signum: int, frame):
        """
        Function called when a Kubernetes signal is received to stop the xApp execution.
        """
        self.logger.info("Received signal {} to stop the xApp.".format(signal.Signals(signum).name))
        self.stop() # Custom xApp termination routine
    
    def start(self):
        """
        Starts the xApp loop.
        """ 
        self._xapp.run()

    def stop(self):
        """
        Terminates the xApp. Can only be called if the xApp is running in threaded mode.
        """
        self._shutdown = True
        self.logger.info("Calling framework termination to unregister the xApp from AppMgr.")
        self._xapp.stop()