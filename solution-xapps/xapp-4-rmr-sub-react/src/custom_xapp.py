
# Imports from OSC libraries
from ricxappframe.xapp_frame import RMRXapp, rmr
from mdclogpy import Logger, Level
from ricxappframe import xapp_rest

# Imports from other libraries
from time import sleep
from threading import Thread
import signal
import json
import requests

class XappRmrSubReact:
    """
    Custom xApp class.
    """
    def __init__(self, thread:bool = True):
        """
        Initializes the custom xApp instance and instatiates the xApp framework object.
        """
        
        # Initializing a logger for the custom xApp instance in Debug level (logs everything)
        self.logger = Logger(name="XappLogSdlRest", level=Level.DEBUG) # The name is included in each log entry, Levels: DEBUG < INFO < WARNING < ERROR
        #self.logger.get_env_params_values() # Getting the MDC key-value pairs from the environment
        self.logger.info("Initializing the xApp.")

        # Initializing custom control variables
        self._shutdown = False # Stops the xApp loop if True
        self._thread = thread # True for executing the xApp loop as a thread
        self._ready = False # True when the xApp is ready to start

        # Instatiating the xApp framework object 
        self._rmrxapp = RMRXapp(
            default_handler=self.default_rmr_handler, # Called when no specific handler is found for an RMR message
            config_handler=self.config_change_handler, # Called when a config change event is detected by inotify
            post_init=self.post_init, # Called during the RMRXapp initialization, right after _BaseXapp is initialized
            rmr_port=4560, # Port for RMR data
            rmr_wait_for_ready=True, # Block xApp initiation until RMR is ready
            use_fake_sdl=False # Use a fake in-memory SDL
        )

        # Starting a threaded HTTP server listening to any host at port 8080 
        self.http_server = xapp_rest.ThreadedHTTPServer("0.0.0.0", 8080)
        self.http_server.handler.add_handler(self.http_server.handler, method="GET", name="config", uri="/ric/v1/config", callback=self.config_handler)
        self.http_server.handler.add_handler(self.http_server.handler, method="GET", name="liveness", uri="/ric/v1/health/alive", callback=self.liveness_handler)
        self.http_server.handler.add_handler(self.http_server.handler, method="GET", name="readiness", uri="/ric/v1/health/ready", callback=self.readiness_handler)
        self.logger.info("Starting HTTP server.")
        self.http_server.start() 

        # Checking if the xApp is ready to start
        while not self._rmrxapp.healthcheck():
            self.logger.info("Waiting 1 second for RMR and SDL to be ready.")
            sleep(1)
        self._ready = True
        self.logger.info("xApp is ready.")

        # Registering handlers for RMR messages
        self._rmrxapp.register_callback(handler=self.active_xapp_handler, message_type=12345)
        
    
    def active_xapp_handler(self, summary: dict, sbuf):
        """
        Handler for the active xapp RMR message.
        """
        self.logger.info("Received active-xapp RMR message with summary: {}.".format(summary))
        self._rmrxapp.rmr_free(sbuf)
        self._rmrxapp.rmr_rts(sbuf, new_payload="Received message correctly".encode()) # Responding to the active-xapp message
    
    def default_rmr_handler(self, summary: dict, sbuf):
        """
        Default RMR message handler.
        """
        self.logger.info("Received RMR message with summary: {}.".format(summary))
        self._rmrxapp.rmr_free(sbuf) # Freeing the RMR message buffer
    
    def config_change_handler(self, rmrxapp:RMRXapp, json: dict):
        """
        Handler for the config change event.
        """
        self.logger.info("Detected a config change event.")

        self.logger.debug(f"Parameters types: self = {type(self)}, rmr_xapp = {type(rmrxapp)}, json = {type(json)}")

        rmrxapp._config_data = json
        self.logger.debug("New config data: {}.".format(json))
    
    def post_init(self, rmr_xapp: RMRXapp):
        """
        Post initialization function.
        """
        self.logger.info("Post initialization started.")

        # Registering a handler for terminating the xApp after TERMINATE, QUIT, or INTERRUPT signals
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGQUIT, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, frame):
        """
        Function called when a Kubernetes signal is received to stop the xApp execution.
        """
        self.logger.info("Received signal {} to stop the xApp.".format(signal.Signals(signum).name))
        self.stop() # Custom xApp termination routine
    
    def config_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP GET /ric/v1/config request.
        """
        self.logger.info("Received GET /ric/v1/config request with content type {}.".format(ctype))
        response = xapp_rest.initResponse(
            status=200, # Status = 200 OK
            response="Config data"
        ) # Initiating HTTP response
        response['payload'] = json.dumps(self._rmrxapp._config_data) # Payload = the xApp config-file
        self.logger.debug("Config handler response: {}.".format(response))
        return response

    def liveness_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP GET /ric/v1/health/alive request.
        """
        self.logger.info("Received GET /ric/v1/health/alive request with content type {}.".format(ctype))
        if self._rmrxapp.healthcheck():
            response = xapp_rest.initResponse(
                status=200, # Status = 200 OK
                response="Liveness"
            ) # Initiating HTTP response
            response['payload'] = json.dumps({"status": "Healthy"}) # Payload = status: Healthy
        else:
            response = xapp_rest.initResponse(
                status=503, # Status = 503 Service Unavailable
                response="Liveness"
            )
            response['payload'] = json.dumps({"status": "Unhealthy"}) # Payload = status: Unhealthy
        self.logger.debug("Liveness handler response: {}.".format(response))
        return response

    def readiness_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP GET /ric/v1/health/ready request.
        """
        self.logger.info("Received GET /ric/v1/health/ready request with content type {}.".format(ctype))
        if self._ready:
            response = xapp_rest.initResponse(
                status=200, # Status = 200 OK
                response="Readiness"
            ) # Initiating HTTP response
            response['payload'] = json.dumps({"status": "Ready"}) # Payload = status: Healthy
        else:
            response = xapp_rest.initResponse(
                status=503, # Status = 503 Service Unavailable
                response="Readiness"
            )
            response['payload'] = json.dumps({"status": "Not ready"})
        self.logger.debug("Readiness handler response: {}.".format(response))
        return response

    def start(self):
        """
        Starts the xApp loop.
        """ 
        self._rmrxapp.run()

    def stop(self):
        """
        Terminates the xApp. Can only be called if the xApp is running in threaded mode.
        """
        self._shutdown = True
        self.logger.info("Calling framework termination to unregister the xApp from AppMgr.")
        self._rmrxapp.stop()
        self.http_server.stop()