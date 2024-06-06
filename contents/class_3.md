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

**EXERCISE X**
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
    "rxMessages": ["RIC_SUB_RESP", "RIC_INDICATION","RIC_SUB_DEL_RESP","TS_QOE_PRED_REQ"],
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
    "rxMessages": ["RIC_SUB_RESP","RIC_SUB_DEL_RESP", "RIC_INDICATION", "TS_UE_LIST"],
    "txMessages": ["RIC_SUB_REQ","RIC_SUB_DEL_REQ", "RIC_CONTROL_REQ", "TS_QOE_PRED_REQ"],
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

**EXERCISE X**
Make xapp3rmrsubact and xapp4rmrsubreact communicate.


# E2 Node subscription
