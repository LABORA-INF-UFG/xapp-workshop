# Class 3: RMR communication and E2 Nodes subscription

At the end of this class, you should be able to:
- Define static route tables for RMR messaging
- Send/receive RMR messages to/from Near-RT RIC components (including other xApps)
- Subscribe and unsubscribe to E2 Nodes

# RMR messaging

The RIC Message Router (RMR) is a lightweight library for communication between OSC's Near-RT RIC components (which includes xApps).
The RMR supports the publish-subscribe pattern and provides an API for communicating without specifying endpoints.
This is done by identifying messages with a message type (`mtype`), which is an integer associated with the hosts who will receive the message.
Some values for `mtype` are already defined in the [RMR implementation](https://github.com/o-ran-sc/ric-plt-lib-rmr/blob/master/src/rmr/common/include/RIC_message_types.h) for specific purposes.
These reserved values also have an associated string, which can be used in the xApp config-file when defining `txMessages` and `rxMessages`.
Below we list some important `mtype` values defined in the RMR.

Health check: already implemented in the `Xapp` and `RMRXapp` classes **(TODO: DOUBLE CHECK)**
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
- `summary[rmr.RMR_MS_SUB_ID]`: the subscription id (`subid`)
- `summary[rmr.RMR_MS_TRN_ID]`: the transaction id, used for replying messages
- `summary[rmr.RMR_MS_MSG_STATUS]`: the message status 
- `summary[rmr.RMR_MS_ERRNO]`: the number identifying the occurred error, if the message status is not ok

A pair or `summary` and `sbuf` (the C pointer to the RMR buffer) refer to an RMR message in the xApp framewok.
Both `Xapp` and `RMRXapp` define four high-level functions for RMR communication:
- `rmr_get_messages`: calls the RMR loop to return a generator that iterates through messages yielding `(summary, sbuf)` tuples
- `rmr_send`: receives a UTF-8 encoded `payload` and a `mtype` to send the RMR message
- `rmr_rts`: returns the received message to the sender, optionally changing the `payload` and `mtype`
- `rmr_free`: frees the `sbuf` RMR buffer

It is important to remid that the `sbuf` must **always** be freed after receiving or sending an RMR message.
The only exception is the `rmr_send` function, which frees `sbuf` after sending. 


A handler for RMR messages must have the format of `handler(summary, sbuf)` to be called by the `RMRXapp` loop, passing `sbuf` as the pointer to the RMR message buffer and `summary` as a dictionary containing the RMR message data and metadata.


# E2 Node subscription
