
# Imports from OSC libraries
from ricxappframe.xapp_frame import RMRXapp, rmr
from mdclogpy import Logger, Level
from ricxappframe import xapp_rest, xapp_subscribe

# Imports from other libraries
from time import sleep
from threading import Thread
import signal
import json
import requests
from typing import Dict

class XappRmrSubReact:
    """
    Custom xApp class.
    """
    def __init__(self, thread:bool = True):
        """
        Initializes the custom xApp instance and instatiates the xApp framework object.
        """
        
        # Initializing a logger for the custom xApp instance in Debug level (logs everything)
        self.logger = Logger(name="XappRmrSubReact", level=Level.DEBUG) # The name is included in each log entry, Levels: DEBUG < INFO < WARNING < ERROR
        #self.logger.get_env_params_values() # Getting the MDC key-value pairs from the environment
        self.logger.info("Initializing the xApp.")

        # Initializing custom control variables
        self._shutdown = False # Stops the xApp loop if True
        self._thread = thread # True for executing the xApp loop as a thread
        self._ready = False # True when the xApp is ready to start
        self.subscription_responses:Dict[int, Dict] = {} # Stores the subscription responses for each E2 node inventory name
        self.sub_id_to_node:Dict[str, str] = {} # Maps subscription IDs to E2 node inventory names
        
        # Instatiating the xApp framework object 
        self._rmrxapp = RMRXapp(
            default_handler=self.default_rmr_handler, # Called when no specific handler is found for an RMR message
            config_handler=self.config_change_handler, # Called when a config change event is detected by inotify
            post_init=self.post_init, # Called during the RMRXapp initialization, right after _BaseXapp is initialized
            rmr_port=4560, # Port for RMR data
            rmr_wait_for_ready=True, # Block xApp initiation until RMR is ready
            use_fake_sdl=False # Use a fake in-memory SDL
        )

        # Registering handlers for RMR messages
        self._rmrxapp.register_callback(handler=self.active_xapp_handler, message_type=30000)
        self._rmrxapp.register_callback(handler=self.ric_indication_handler, message_type=12050)

        # Registering a handler for terminating the xApp after TERMINATE, QUIT, or INTERRUPT signals
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGQUIT, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Starting a threaded HTTP server listening to any host at port 8080 
        self.http_server = xapp_rest.ThreadedHTTPServer("0.0.0.0", 8080)
        self.http_server.handler.add_handler(self.http_server.handler, method="GET", name="config", uri="/ric/v1/config", callback=self.config_handler)
        self.http_server.handler.add_handler(self.http_server.handler, method="GET", name="liveness", uri="/ric/v1/health/alive", callback=self.liveness_handler)
        self.http_server.handler.add_handler(self.http_server.handler, method="GET", name="readiness", uri="/ric/v1/health/ready", callback=self.readiness_handler)
        self.http_server.handler.add_handler(self.http_server.handler, method="POST", name="sub_resp", uri="/ric/v1/subscriptions/response", callback=self.subscription_response_handler)
        self.http_server.handler.add_handler(self.http_server.handler, method="GET", name="resubscribe", uri="/ric/v1/resubscribe", callback=self.resubscribe_handler)
        self.logger.info("Starting HTTP server.")
        self.http_server.start() 

        # xApp is ready to start
        self._ready = True
        self.logger.info("xApp is ready.")
        
    # ------------------ RMR MESSAGE HANDLERS

    def active_xapp_handler(self, rmr_xapp: RMRXapp, summary: dict, sbuf):
        """
        Handler for the active xapp RMR message.
        """
        self.logger.info("Received active-xapp RMR message with summary: {}.".format(summary))
        rmr_xapp.rmr_rts(sbuf, new_payload="Received message correctly".encode(), new_mtype=30001) # Responding to the active-xapp message
        rmr_xapp.rmr_free(sbuf)
    
    def default_rmr_handler(self, rmrxapp: RMRXapp, summary: dict, sbuf):
        """
        Default RMR message handler.
        """
        self.logger.info("Received RMR message with summary: {}.".format(summary))
        rmrxapp.rmr_free(sbuf) # Freeing the RMR message buffer
    
    def ric_indication_handler(self, rmrxapp: RMRXapp, summary: dict, sbuf):
        """
        Handler for the E2 node RIC indication.
        """
        self.logger.info("Received E2 node RIC indication, responding with a RIC Control")
        rmrxapp.rmr_rts(sbuf, new_mtype=12040)
        rmrxapp.rmr_free(sbuf)

    # ------------------ RMRXAPP INTERNAL FUNCTIONS

    def config_change_handler(self, rmrxapp:RMRXapp, json: dict):
        """
        Handler for the config change event.
        """
        self.logger.info("Detected a config change event.")

        rmrxapp._config_data = json
        self.logger.debug("New config data: {}.".format(json))
    
    def post_init(self, rmrxapp: RMRXapp):
        """
        Post initialization function.
        """
        self.logger.info("Post initialization called.")

    # ------------------ E2 NODE SUBSCRIPTIONS

    def subscribe_to_e2_nodes(self):
        """
        Subscribes to all available E2 nodes.
        """

        # DEPRECATED - WE DO NOT USE xapp_subscribe BECAUSE IT DOES NOT WORK
        # self.subscriber = xapp_subscribe.NewSubscriber(
        #     uri="http://service-ricplt-submgr-http.ricplt.svc.cluster.local:8088/ric/v1/subscriptions",
        #     local_port=8080,
        #     rmr_port=4560
        # )

        e2_nodes = self._rmrxapp.GetListNodebIds()
        sub_trs_id = self._rmrxapp.sdl_get(namespace="xapp4rmrsubreact", key="subscription_transaction_id")
        if sub_trs_id is None:
            sub_trs_id = 54321
        for node in e2_nodes:
            self.logger.info(f"Subscribing to node {node.inventory_name}") # We use the inventory name as the node ID 
            
            # DEPRECATED - WE DO NOT USE xapp_subscribe BECAUSE IT DOES NOT WORK
            # # Workouround class to send the correct subscription request body,
            # # since the SubscriptionParams object has the wrong keys (lowercase and with underscores)
            # class Params:
            #     def __init__(self, my_dict):
            #         self.my_dict = my_dict
            #     def to_dict(self):
            #         return self.my_dict
            
            # # Sending the subscription request
            # data, reason, status = self.subscriber.Subscribe(
            #     subs_params= Params(self.generate_subscription_request(node.inventory_name, sub_trs_id))
            #     # subs_params = self.generate_sub_params(
            #     #     subscriber=self.subscriber,
            #     #     inventory_name=node.inventory_name,
            #     #     subscription_transaction_id=sub_trs_id
            #     # )
            # )
            # self.subscription_responses[node.inventory_name] = json.loads(data) # {"SubscriptionId": "my_string_id", "SubscriptionInstances": null}

            # Sending the subscription request
            resp = requests.post(
                "http://service-ricplt-submgr-http.ricplt.svc.cluster.local:8088/ric/v1/subscriptions",
                json=self.generate_subscription_request(node.inventory_name, sub_trs_id)
            )
            data = resp.json() # {"SubscriptionId": "my_string_id", "SubscriptionInstances": null}
            status = resp.status_code
            reason = resp.reason

            self.sub_id_to_node[data["SubscriptionId"]] = node.inventory_name
            self.subscription_responses[node.inventory_name] = data
            self.logger.debug(f"Subscription response from {node.inventory_name}: status = {status}, reason = {reason}, data = {data}")
            self._rmrxapp.sdl_set(namespace="xapp4rmrsubreact", key="subscription_transaction_id", value=sub_trs_id+1) # Update sub_trs_id on SDL
    
    def unsubscribe_from_e2_nodes(self):
        """
        Unsubscribes from all subscribed E2 nodes (stored in the self.subscription_responses dict).
        """
        
        # DEPRECATED - WE DO NOT USE xapp_subscribe BECAUSE IT DOES NOT WORK
        # # Using a workaround to fix the unsubscribe URI because the framework adds /subscription/
        # self.subscriber.uri = "http://service-ricplt-submgr-http.ricplt.svc.cluster.local:8088/ric/v1"
        # for node in self.subscription_responses.keys():
        #     data, reason, status = self.subscriber.UnSubscribe(subs_id=self.subscription_responses[node]["SubscriptionId"])
        #     self.logger.info(f"Unsubscribe from node {node}: status = {status}, reason = {reason}, data = {data}")
        
        for sub_id in self.sub_id_to_node.keys():
            resp = requests.delete(
                f"http://service-ricplt-submgr-http.ricplt.svc.cluster.local:8088/ric/v1/subscriptions/{sub_id}"
            )
            status = resp.status_code
            reason = resp.reason
            self.logger.info(f"Unsubscribe from sub id {sub_id}: status = {status}, reason = {reason}")

    # ------------------ SIGNAL HANDLERS

    def _handle_signal(self, signum: int, frame):
        """
        Function called when a Kubernetes signal is received to stop the xApp execution.
        """
        self.logger.info("Received signal {} to stop the xApp.".format(signal.Signals(signum).name))
        self.stop() # Custom xApp termination routine
    
    # ------------------ HTTP HANDLERS

    def resubscribe_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP GET /ric/v1/resubscribe request.
        """
        self.logger.info("Received GET /ric/v1/resubscribe request, resubscribing to E2 Nodes")
        self.unsubscribe_from_e2_nodes()
        self.subscribe_to_e2_nodes()
        response = xapp_rest.initResponse(
            status=200, # Status = 200 OK
            response="ACK subscription response"
        ) # Initiating HTTP response
        return response
    
    def subscription_response_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP POST /ric/v1/subscriptions/response request.
        """
        sub_resp = json.loads(data.decode())
        self.logger.info("Received POST /ric/v1/subscriptions/response request with data {}.".format(sub_resp))
        nodeb = self.sub_id_to_node[sub_resp["SubscriptionId"]]
        self.subscription_responses[nodeb]["SubscriptionInstances"] = sub_resp["SubscriptionInstances"]
        response = xapp_rest.initResponse(
            status=200, # Status = 200 OK
            response="ACK subscription response"
        ) # Initiating HTTP response
        return response

    def config_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP GET /ric/v1/config request.
        """
        #self.logger.info("Received GET /ric/v1/config request with content type {}.".format(ctype))
        response = xapp_rest.initResponse(
            status=200, # Status = 200 OK
            response="Config data"
        ) # Initiating HTTP response
        response['payload'] = json.dumps(self._rmrxapp._config_data) # Payload = the xApp config-file
        #self.logger.debug("Config handler response: {}.".format(response))
        return response

    def liveness_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP GET /ric/v1/health/alive request.
        """
        #self.logger.info("Received GET /ric/v1/health/alive request with content type {}.".format(ctype))
        response = xapp_rest.initResponse(
            status=200, # Status = 200 OK
            response="Liveness"
        ) # Initiating HTTP response
        response['payload'] = json.dumps({"status": "Healthy"}) # Payload = status: Healthy
        #self.logger.debug("Liveness handler response: {}.".format(response))
        return response

    def readiness_handler(self, name:str, path:str, data:bytes, ctype:str):
        """
        Handler for the HTTP GET /ric/v1/health/ready request.
        """
        #self.logger.info("Received GET /ric/v1/health/ready request with content type {}.".format(ctype))
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
        #self.logger.debug("Readiness handler response: {}.".format(response))
        return response

    # ------------------ START AND STOP

    def start(self):
        """
        Starts the xApp loop.
        """ 
        self.subscribe_to_e2_nodes()
        self._rmrxapp.run()    

    def stop(self):
        """
        Terminates the xApp. Can only be called if the xApp is running in threaded mode.
        """
        self._shutdown = True
        self.unsubscribe_from_e2_nodes()
        self.logger.info("Calling framework termination to unregister the xApp from AppMgr.")
        self._rmrxapp.stop()
        self.http_server.stop()

    # ------------------ SUBSCRIPTION REQUEST JSON
    
    # Hard coded as workaround for the wrong keys in the SubscriptionParams object
    def generate_subscription_request(self, inventory_name, subscription_transaction_id):
        return {
            "SubscriptionId":"",
            "ClientEndpoint": {
                "Host":"service-ricxapp-xapp4rmrsubreact-http.ricxapp",
                "HTTPPort":8080,
                "RMRPort":4560
            },
            "Meid":inventory_name, # nobe B inventory_name
            "RANFunctionID":1, # Default = 0
            "E2SubscriptionDirectives":{ # Optional
                "E2TimeoutTimerValue":2, # Default = 2
                "E2RetryCount":2, # Default = 2
                "RMRRoutingNeeded":True # Default = True
            },
            "SubscriptionDetails":[ # Can make multiple subscriptions
                {
                    "XappEventInstanceId":subscription_transaction_id, # "Transaction id"
                    "EventTriggers":[2], # Default = [0]
                    "ActionToBeSetupList":[
                        {
                            "ActionID": 1,
                            "ActionType": "insert", # Default = "report"
                            "ActionDefinition": [3], # Default = [0]
                            "SubsequentAction":{
                                "SubsequentActionType":"continue",
                                "TimeToWait":"w10ms" # Default = "zero"
                            }
                        }
                    ]
                }
            ]
        }
    
    # DEPRECATED - WE DO NOT USE xapp_subscribe BECAUSE IT DOES NOT WORK
    # # Not used because the SubscriptionParams object has the wrong keys
    # def generate_sub_params(self, subscriber:xapp_subscribe.NewSubscriber, inventory_name, subscription_transaction_id):
    #     client_endpoint = subscriber.SubscriptionParamsClientEndpoint(
    #         host="service-ricxapp-xapp4rmrsubreact-http.ricxapp",
    #         http_port=8080,
    #         rmr_port=4560
    #     )

    #     e2_subscription_directives = subscriber.SubscriptionParamsE2SubscriptionDirectives(
    #         e2_timeout_timer_value=2,
    #         e2_retry_count=2,
    #         rmr_routing_needed=True
    #     )

    #     subsequent_action = subscriber.SubsequentAction(
    #         subsequent_action_type="continue",
    #         time_to_wait="w10ms"
    #     )

    #     action_to_be_setup = subscriber.ActionToBeSetup(
    #         action_id=1,
    #         action_type="insert",
    #         action_definition=(3,), 
    #         subsequent_action=subsequent_action
    #     )

    #     subscription_details = subscriber.SubscriptionDetail(
    #         xapp_event_instance_id=subscription_transaction_id,
    #         event_triggers=(2,),
    #         action_to_be_setup_list=action_to_be_setup
    #     )

    #     subscription_params = subscriber.SubscriptionParams(
    #         subscription_id="",
    #         client_endpoint=client_endpoint,
    #         meid=inventory_name,
    #         ran_function_id = 1,
    #         e2_subscription_directives=e2_subscription_directives,
    #         subscription_details=subscription_details
    #     )

    #     self.logger.info (f"Sub params: {subscription_params.to_dict()}")

    #     return subscription_params