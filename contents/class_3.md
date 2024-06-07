# Class 3: RMR communication and E2 Nodes subscription

At the end of this class, you should be able to:
- Define static route tables for RMR messaging
- Send/receive RMR messages to/from Near-RT RIC components (including other xApps)
- Subscribe and unsubscribe to E2 Nodes

# RMR messaging

The RIC Message Router (RMR) is a lightweight library for communication between OSC's Near-RT RIC components (which includes xApps).
The RMR supports the publish-subscribe pattern and provides an API for communicating without specifying endpoints.
This is done by identifying messages with a message type (`mtype`), which is an integer and a name already known by the Near-RT RIC components to transport the message appropriately.
The defined values for `mtype` can be found in the [RMR implementation](https://github.com/o-ran-sc/ric-plt-lib-rmr/blob/master/src/rmr/common/include/RIC_message_types.h).
To enable the RMR communication of the xApp, the names of the `mtypes` it can transmit or receive must be defined in the `rmrdata` section of the config-file, in the `txMessages` and `rxMessages` arrays, respectively.

Below we list some important `mtype` values defined in the RMR.

Health check: already handled inisde the `Xapp` and `RMRXapp` classes
- `100` - `RIC_HEALTH_CHECK_REQ`: Health check request
- `101` - `RIC_HEALTH_CHECK_RESP`: Health check response

E2 Node subscription: sent/received to/from the Subscription Manager (SubMgr) 
- `12010` - `RIC_SUB_REQ`: Subscription request
- `12011` - `RIC_SUB_RESP`: Subscription response
- `12012` - `RIC_SUB_FAILURE`: Subscription failure
- `12020` - `RIC_SUB_DEL_REQ`: Subscription delete request
- `12021` - `RIC_SUB_DEL_RESP`: Subscription delete response
- `12022` - `RIC_SUB_DEL_FAILURE`: Subscription delete failure

E2 Node control loop: sent/received to/from the E2 Nodes via the E2 Termination (E2Term)
- `12040` - `RIC_CONTROL_REQ`
- `12041` - `RIC_CONTROL_ACK`
- `12042` - `RIC_CONTROL_FAILURE`
- `12050` - `RIC_INDICATION`

To manage publish-subscribe communication, the RMR identifies a subscription with a `subid`, which is an integer.
The main use for `subid` is subscribing to E2 Nodes, which consists of sending a subscription request to the SubMgr and receiving a response with the generated `subid`. 

In this class, we will make two xApps (`xapp3rmrsubact` and `xapp4rmrsubreact`) communicate with each other using RMR messages.
We can not define new `mtypes`, since they need to be implemented in the RMR library of the Routing Manager (RtMgr) to distribute routes for the `mtype` numeric values.
Therefore, we use two already defined `mtypes` from [OSC's traffic steering xApp](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-app-ts/en/latest/user-guide.html):
- `30000` - `TS_UE_LIST`
- `30001` - `TS_QOE_PRED_REQ`

------------------------------------------------------------------------ **EXERCISE 1** ------------------------------------------------------------------------

Edit the config-file from `xapp3rmrsubact` (located in `xapp-3-rmr-sub-act/init/config-file.json`) and `xapp4rmrsubreact` (located in `xapp-4-rmr-sub-react/init/config-file.json`) to add the `mtypes` for them to communicate using RMR:
- `xapp3rmrsubact` must send `TS_UE_LIST` messages to `xapp4rmrsubreact`
- `xapp4rmrsubreact` must send `TS_QOE_PRED_REQ` to `xapp3rmrsubact`

<p>
<details>
<summary>Solution</summary>

`xapp3rmrsubact` config-file `rmrdata` port:

```json
{
    "name": "rmrdata",
    "container": "xapp3rmrsubactcontainer",
    "port": 4560,
    "rxMessages": ["RIC_SUB_RESP","RIC_SUB_DEL_RESP","TS_QOE_PRED_REQ"],
    "txMessages": ["RIC_SUB_REQ","RIC_SUB_DEL_REQ", "TS_UE_LIST"],
    "policies": [1],
    "description": "rmr data port"
}
```

`xapp4rmrsubreact` config-file `rmrdata` port:

```json
{
    "name": "rmrdata",
    "container": "xapp4rmrsubreactcontainer",
    "port": 4560,
    "rxMessages": ["RIC_SUB_RESP","RIC_SUB_DEL_RESP", "TS_UE_LIST"],
    "txMessages": ["RIC_SUB_REQ","RIC_SUB_DEL_REQ", "TS_QOE_PRED_REQ"],
    "policies": [1],
    "description": "rmr data port"
}
```

</details>
</p>

## Route table

The RMR relies on a route table to reach endpoints.
This table is dynamically updated by RtMgr every time an xApp or Near-RT RIC component goes up or down, but it can also be statically defined in a `.rt` file, whose path must be in the `RMR_SEED_RT` environmental variable.

The route table is a list of entry records defining endpoints for every `mtype`.
There are two kinds of entries: `mse`, which supports subscriptions, and `rte`, which does not support subscriptions and is deprecated, so it might be removed by OSC anytime.
Therefore, we address only `mse` in this workshop.

The `mse` entry record is a line in the form of:
```
mse | <mtype> [,<sender-endpoint>] | <subid> | <endpoint-group>[;<endpoint-group>;...]
```

where
- `mtype` is the integer identifying the message type
- `sender-endpoints` is an optional set of endpoints of sender applications
- `subid` is an integer identifying the subscription, which must be `-1` if there is no current subscription
- `endpoint-group` is a set of endpoints that will receive the RMR message

At least one endpoint should be defined for sending an RMR message.
The RMR groups endpoints to send messages using two approaches:
- Fanout among groups: the message is broadcast to every group  
- Round-robin inside the group: only one endpoint in the group (selected in a round-robin way) will receive the message, which is useful for load balancing

For example:
```
mse | 12040 xapp3:4560 | -1 | A:4560,B;C,D
```

We assume `xapp3`, `A`, `B`, `C`, and `D` are defined hostnames.
When `xapp3` sends a message of type `12040` (RIC Control Request), it is received only by `A` and `C`.
Sending another message of the same type will result in `B` and `D` receiving the message.
Note that not defining the endpoint port will make RMR assume the standard `4560` RMR data port.

To contain the entry records, the route table has some metadata in its structure:

```
newrt | start [ | <table-id>]
<entry-record-1>
<entry-record-2>
...
newrt | end [ | <number-of-entries>]
```

Where `table-id` is a string with the name of the table and `number-of-entries` has the number of entry records of the table.
Both are optional and used to verify the table's integrity.

This is an example of a full route table to send RMR messages of type `12345` to `xapp3rmrsubact`: **(TODO: TEST)**

```
newrt | start | my_table_1
mse | 12345 | -1 | service-ricxapp-xapp4rmrsubreact-rmr.ricxapp:4560
newrt | end | 1
```

## Handling RMR messages

The RMR library is implemented in C and called by the Python xApp framework using wrappers implemented in `ricxappframe.rmr`.
However, the RMR functions are abstracted by the `Xapp` and `RMRXapp` classes to make transparent the low-level handling of message buffers and metadata.

When initializing `Xapp` or `RMRXapp`, a threaded RMR loop (implemented in `ricxappframe.xapp_rmr`) is started to continuosly look for new messages by reading the RMR stream buffer, acessable via a C pointer (of `c_void_p` type).
Despite this, it is common to only refer to the buffer when freeing it, since all data and metadata about RMR messages are present in a `summary` dictionary generated by the framework.
The `summary` fields are accessed through keys defined in the `rmr` library:
- `summary[rmr.RMR_MS_PAYLOAD]`: the payload (a bytes object encoded in UTF-8)
- `summary[rmr.RMR_MS_PAYLOAD_LEN]`: the number of bytes of the payload
- `summary[rmr.RMR_MS_PAYLOAD_MAX]`: the maximum number of bytes usable in the payload
- `summary[rmr.RMR_MS_SUB_ID]`: the subscription id (`subid`)
- `summary[rmr.RMR_MS_TRN_ID]`: the transaction id, used for replying messages
- `summary[rmr.RMR_MS_MSG_STATE]`: the state of the message, an integer 
- `summary[rmr.RMR_MS_MSG_STATUS]`: the message state, but converted to an string (e.g. `"RMR_OK"`)
- `summary[rmr.RMR_MS_ERRNO]`: an ID to the occurred error, if the message status is not ok
- `summary[rmr.RMR_MS_MSG_SOURCE]`: the hostname of the sender
- `summary[rmr.RMR_MS_MEID]`: the managed entity (e.g. a gNB) ID, in bytes

A buffer is allocated for a RMR message everytime one is sended or received.
This buffer is referred to as `sbuf`, a void C pointer.
When handling RMR messages, a pair or `summary` and `sbuf` are sufficient to access data and metadata and free the buffer.
Both `Xapp` and `RMRXapp` define four high-level functions for RMR communication:
- `rmr_get_messages`: calls the RMR loop to return a generator that iterates through messages yielding `(summary, sbuf)` tuples
- `rmr_send`: receives a UTF-8 encoded `payload` and a `mtype` to send the RMR message
- `rmr_rts`: returns the received message to the sender, optionally changing the `payload` and `mtype`
- `rmr_free`: frees the `sbuf` RMR buffer

It is important to remind that the `sbuf` must **always** be freed after receiving or sending an RMR message.
The only exception is the `rmr_send` function, which frees `sbuf` after sending.
Freeing an already freed `sbuf` may break the xApp. 

The `RMRXapp` implements a loop of checking for received RMR messages and calling the registered handlers, while a developer using the `Xapp` class must implement it.
Below we provide a function for the `Xapp` that works identically to executing the `RMRXapp` loop one single time.
To continuosly check for RMR messages, it needs to be continuously called.

```python
def receive_RMR_messages(self, xapp: Xapp, dispatch:dict):
    for summary, sbuf in xapp.rmr_get_messages():
        func = dispatch.get(summary[rmr.RMR_MS_MSG_TYPE], default_handler)
        func(xapp, summary, sbuf)
```

In this function, `xapp` is the `Xapp` framework object and `dispatch` is a dictionary in the format of `mtype: handler_function`.
Note that, if no handler function is defined for the received `mtype`, a `default_handler` is called.
The handlers (including the default handler) must have the same signature of a handler registered in the `RMRXapp` dispatcher, i.e. receiving `xapp`, `summary`, and `sbuf`, in this order.

This is a handler that logs the received message and return it to the sender with a new payload:

```python
def simple_handler(self, xapp:Xapp, summary:dict, sbuf):
    self.logger.info(
        "Received RMR message of type {} with payload = {}".format(
            summary[rmr.RMR_MS_MSG_TYPE],
            summary[rmr.RMR_MS_PAYLOAD].decode()
        )
    )
    xapp.rmr_rts(sbuf, new_payload="ACK".encode()) # Return to sender
    xapp.rmr_free(sbuf)
```

Note that the same buffer (`sbuf`) is used when replying to the sender and is freed only after the reply.

To register this handler in the `Xapp` (assuming the `receive_RMR_messages` function described before), we only need to insert it on the `dispatch` dictionary.
The code below assumes that `simple_handler` must be registered to the `mtype` of value `12345`. 

```python
dispatch = {}
dispatch[12345] = simple_handler
```

Similarly, on the `RMRXapp` class, we just have to call the `register_callback` method from the `rmrxapp` framework object:

```python
rmrxapp.register_callback(handler=simple_handler, message_type=12345)
```

## RMR exercises

------------------------------------------------------------------------ **EXERCISE 2** ------------------------------------------------------------------------

Edit the source code from `xapp3rmrsubact` (located in `xapp-3-rmr-sub-act/src/customxapp.py`) to implement a loop that, every second, receives RMR messages, sends an RMR message of type `TS_UE_LIST` (`30000`).
Tip: receive the RMR messages using the `_receive_RMR_messages` function from the `XappRmrSubAct` class.

<p>
<details>
<summary>Solution</summary>

Edit the `_loop` function from `XappRmrSubAct` class to:

```python
def _loop(self):  
    while not self._shutdown: # True since custom xApp initialization until stop() is called
        self._receive_RMR_messages() # Call handlers for all received RMR messages
        self._xapp.rmr_send(payload="Message of type 30000 from the active xApp".encode(), mtype=30000): # Sends an RMR message of type 30000
        sleep(1) # Sleeps for 1 second
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 3** ------------------------------------------------------------------------

Edit the source code from `xapp3rmrsubact` (located in `xapp-3-rmr-sub-act/src/customxapp.py`) to implement a handler for RMR messages of type `TS_QOE_PRED_REQ` (`30001`) that logs the received payload.
This handler will be called by the `_receive_RMR_messages` method from the previous exercise. 
Tip: register the handler in the `_dispatch` dictionary (it has the format of `{rmr_mtype: handler_function}`) during the `XappRmrSubAct` initialization. 

<p>
<details>
<summary>Solution</summary>

Implementing the handler as a method of `XappRmrSubAct` class:

```python
def _handle_react_xapp_msg(self, xapp:Xapp, summary:dict, sbuf):
    rcv_payload = summary[rmr.RMR_MS_PAYLOAD].decode() # Decodes the RMR message payload
    self.logger.info("Received message of type 30001 with payload: {}".format(rcv_payload))
    xapp.rmr_free(sbuf) # Frees the RMR message buffer
```

Edit the `__init__` function from `XappRmrSubAct` class to register the handler in the `_dispatch` dictionary:

```python
# Registering handlers for RMR messages
self._dispatch = {} # Dictionary for calling handlers of specific message types
self._dispatch[30001] = self._handle_react_xapp_msg
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 4** ------------------------------------------------------------------------

Edit the source code from `xapp4rmrsubreact` (located in `xapp-4-rmr-sub-react/src/customxapp.py`) to implement a handler for RMR messages of type `TS_UE_LIST` (`30000`) that logs the received payload and replies the sender with a message of type `TS_QOE_PRED_REQ` (`30001`) containing a different payload.
Tip: register the handler using the `register_callback` method from the `RMRXapp` object during the `XappRmrSubAct` initialization.

<p>
<details>
<summary>Solution</summary>

Implementing the handler as a method of `XappRmrSubReact` class:

```python
def active_xapp_handler(self, rmr_xapp: RMRXapp, summary: dict, sbuf):
    self.logger.info("Received active-xapp RMR message with payload: {}.".format(summary[rmr.RMR_MS_PAYLOAD].decode()))
    rmr_xapp.rmr_rts(sbuf, new_payload="Received message correctly".encode(), new_mtype=30001) # Responding to the active-xapp message
    rmr_xapp.rmr_free(sbuf)
```

Edit the `__init__` function from `XappRmrSubReact` class to register the handler:

```python
# Registering handlers for RMR messages
self._rmrxapp.register_callback(handler=self.active_xapp_handler, message_type=30000)
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 5** ------------------------------------------------------------------------

Run and check the logs of both `xapp3rmrsubact` and `xapp4rmrsubreact` xApps.
Tip: use the `update_xapp.sh` and `log_xapp.sh` script at the xApps directories.

<p>
<details>
<summary>Solution</summary>

Entering the `xapp3rmrsubact` xApp directory (assuming you are at this repository root) and executing its installation and log scripts:

```bash
cd exercise-xapps/xapp-3-rmr-sub-act
bash update_xapp.sh
bash log_xapp.sh
```

Entering the `xapp4rmrsubreact` xApp directory (assuming you are at this repository root) and executing its installation and log scripts:

```bash
cd exercise-xapps/xapp-4-rmr-sub-react
bash update_xapp.sh
bash log_xapp.sh
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 6** ------------------------------------------------------------------------

Prepare the ambient for the next section by uninstall `xapp3rmrsubact` and `xapp4rmrsubreact`:

```bash
dms_cli uninstall xapp3rmrsubact ricxapp
dms_cli uninstall xapp4rmrsubreact ricxapp
```

# E2 Node subscription

In OSC's Near-RT RIC, the xApps communicate with E2 Nodes using subscriptions.
After subscribing to an E2 Node, it can send messages to the xApp via the E2 Termination (E2Term), which can respond with control messages, for example.

An xApp should subscribe to an E2 Node by sending a **subscription request** (a JSON) to SubMgr via HTTP POST.
The `ricxappframe` has a library for subscriptions (`ricxappframe.xapp_subscribe`), but its actual version has some issues: it sends a subscription request with the wrong keys (using snake case instead of camel case) and the unsubscribe method uses the wrong URI (adding `/subscriptions` to a path that already has it).
Therefore, in this workshop, we choose to subscribe and unsubscribe from E2 Nodes directly sending HTTP messages through the [requests Python library](https://pypi.org/project/requests/).

## Identifying E2 Nodes

To send a subscription, the `inventory_name` of the E2 Node (eNB or gNB) must be informed as its identifier.
The `inventory_name` is registered by the E2 Node in the SDL when connecting to the Near-RT RIC.
Consulting the SDL to obtain the `inventory_name` for all E2 Nodes can be done by executing the `GetListNodebIds` method of `Xapp` and ``RMRXapp` classes.
It will return a list of `NbIdentity`, an object containing the `inventory_name` as its atribute.
Below we exemplify a method for `xapp4rmrsubreact` xApp that logs all registered values of `inventory_name`:

```python
def log_inventory_names(self, rmrxapp: RMRXapp):
    nb_ids = rmrxapp.GetListNodebIds()
    self.logger.info(f"Available E2 Nodes: {[nb_id.inventory_name for nb_id in nb_ids]}")   
```

## Subscribing to E2 Nodes

The subscription request is sent to the SubMgr so it generates a subscription ID and triggers RtMgr to update the routes between the xApp and the E2 Node with the generated `subid`.
The subscription request is a JSON containing informations about how the E2 Node should inform the xApp.
It is sent as body of an HTTP POST to SubMgr's HTTP service, at the path `ric/v1/subscriptions`.
The complete URI is: `http://service-ricplt-submgr-http.ricplt.svc.cluster.local:8088/ric/v1/subscriptions`.
Below we have the subscription request used for subscribing to the modified E2SIM running in the [Blueprint v1](https://github.com/LABORA-INF-UFG/openran-br-blueprint/wiki/OpenRAN@Brasil-Blueprint-v1).

```python
{
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
```

Note that we specify a `subscription_transaction_id` as `XappEventInstanceId`.
This value is used only to identify the transaction of requesting a subscription and can be random.

The subscription request response is a JSON with two fields:
- `"SubscriptionId"`: a string with the subscription ID
- `"SubscriptionInstances"`: a dictionary with information about the subscription, generally null at first

After a moment, the SubMgr should send an HTTP POST to the xApp at the path `/ric/v1/subscriptions/response` containing the same `"SubscriptionId"` and an updated `"SubscriptionInstances"`.
If there is any error during the subscription, such as the RtMgr not being able to create routes for the xApp, it is contained in the `"SubscriptionInstances"` dictionary.
The `xapp4rmrsubreact` already has a regitered HTTP handler to receive subscription responses.

## Unsubscribing to E2 Nodes

It is important to delete a subscription that is no longer needed (e.g. when the xApp terminates) so we avoid having problems with the next subscriptions.
To unsubscribe, we send a **subscription delete request** to the SubMgr, which consists of sending HTTP DELETE at the `/ric/v1/subscriptions/<SUB_ID>` path.
The `"SubscriptionId"` field from both subscription responses should be put in the place of `<SUB_ID>`.
The complete URI is: `http://service-ricplt-submgr-http.ricplt.svc.cluster.local:8088/ric/v1/subscriptions/<SUB_ID>`.
This will trigger RtMgr to erase the routes between the xApp and the E2 Node, while also informing the E2 Node that the subscription has ended.

## Subscription exercises

In this class, we will modify the source code of `xapp4rmrsubreact`, so it:
- Subscribes to all available E2 Nodes during start up
- Deletes every active subscription when terminating
- Deletes every active subscription and then subscribes to all available E2 Nodes after being triggered by an HTTP GET at path `ric/v1/resubscribe`.

The next exercises assume you are in the `xapp4rmrsubreact` directory (located at `exercise-xapps/xapp-4-rmr-sub-react/`).

------------------------------------------------------------------------ **EXERCISE 7** ------------------------------------------------------------------------

Edit the `xapp4rmrsubreact` config-file so the xApp can receive `RIC_INDICATION` and send `RIC_CONTROL_REQ`.

<p>
<details>
<summary>Solution</summary>

The `rmrdata` port should be:

```json
{
    "name": "rmrdata",
    "container": "xapp4rmrsubreactcontainer",
    "port": 4560,
    "rxMessages": ["RIC_SUB_RESP","RIC_SUB_DEL_RESP", "TS_UE_LIST", "RIC_INDICATION"],
    "txMessages": ["RIC_SUB_REQ","RIC_SUB_DEL_REQ", "TS_QOE_PRED_REQ", "RIC_CONTROL_REQ"],
    "policies": [1],
    "description": "rmr data port"
}
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 8** ------------------------------------------------------------------------

During the `start` method of `xapp4rmrsubreact` (which is called after initializing the xApp), subscribe to all E2 Nodes using the `subscribe_to_e2_nodes` function.
Note that the `self._rmrxapp.run()` execution will block the `start` method.

Also, complete the `subscribe_to_e2_nodes` function, which is lacking:
- Consulting the E2 Node IDs from the SDL, which should be stored in the `e2_nodes` variable
- Sending the subscription request using the `request` library and saving its response in the `resp` variable

<p>
<details>
<summary>Solution</summary>

The `start` method should be:

```python
def start(self):
    """
    Starts the xApp loop.
    """ 
    self.subscribe_to_e2_nodes()
    self._rmrxapp.run() 
```

The `subscribe_to_e2_nodes` method should be:

```python
def subscribe_to_e2_nodes(self):
    """
    Subscribes to all available E2 nodes.
    """
    e2_nodes = self._rmrxapp.GetListNodebIds()
    
    sub_trs_id = self._rmrxapp.sdl_get(namespace="xapp4rmrsubreact", key="subscription_transaction_id")
    if sub_trs_id is None:
        sub_trs_id = 54321
    for node in e2_nodes:
        self.logger.info(f"Subscribing to node {node.inventory_name}") # We use the inventory name as the node ID 

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
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 9** ------------------------------------------------------------------------

During the `stop` method of `xapp4rmrsubreact` (which is called during the xApp termination), unsubscribe of all E2 Nodes using the `unsubscribe_from_e2_nodes` method.
Do this as the first step of the `stop` routine.

Also, complete the `unsubscribe_from_e2_nodes` method, which is lacking:
- Sending the subscription delete request using the `request` library and saving its response in the `resp` variable

<p>
<details>
<summary>Solution</summary>

The `stop` method should be:

```python
def stop(self):
    """
    Terminates the xApp. Can only be called if the xApp is running in threaded mode.
    """
    self._shutdown = True
    self.unsubscribe_from_e2_nodes()
    self.logger.info("Calling framework termination to unregister the xApp from AppMgr.")
    self._rmrxapp.stop()
    self.http_server.stop()
```

The `unsubscribe_from_e2_nodes` method should be:

```python
def unsubscribe_from_e2_nodes(self):
    """
    Unsubscribes from all subscribed E2 nodes (stored in the self.subscription_responses dict).
    """
            
    for sub_id in self.sub_id_to_node.keys():
        resp = requests.delete(
            f"http://service-ricplt-submgr-http.ricplt.svc.cluster.local:8088/ric/v1/subscriptions/{sub_id}"
        )
        status = resp.status_code
        reason = resp.reason
        self.logger.info(f"Unsubscribe from sub id {sub_id}: status = {status}, reason = {reason}")
```

</details>
</p>

----------------------------------------------------------------------- **EXERCISE 10** -----------------------------------------------------------------------

Run `xapp4rmrsubreact` and get its logs:

```bash
bash update_xapp.sh
bash log_xapp.sh
```

Check the logs of both E2SIMs by executing:

```bash
bash check_e2_node.sh 1
bash check_e2_node.sh 2
```

If the xApp is running for a few seconds and its logs show that the subscription could not be done, this is due to some instabilities in the xApp pipeline and/or the Near-RT RIC components (SubMgr, AppMgr) and the E2SIMs.
As workaround, try triggering the unsubscribe and subscribe routine of `xapp4rmrsubreact` by sending a `curl` to it with the script below:

```bash
bash resubscribe.sh
```

If nothing worked, try restarting the E2SIMs and some important Near-RT RIC components with the script below:

```bash
bash restart_e2sims.sh
```