# Class 2: xApp overview, logging, SDL, and REST
At the end of this class, you should be able to:
- Understand the structure of an xApp written using OSC's Python xApp Framework
- Log messages from the xApp using OSC's `mdclogpy` library
- Create, retrieve, update, and delete data using the Shared Data Layer (SDL) API
- Develop REST interaction (as server and client) for the xApp

All exercises in this class refer to the `xapp2logsdlrest` xApp, located in `xapp-workshop/exercise-xapps/xapp-2-log-sdl-rest` folder.
It is highly advisable to change the current directory to the xApp directory as every command assumes that it is the actual directory.

# xApp architecture

In this workshop, all custom xApps have an entry point defined in `setup.py` as the `launchXapp` function from the `src/main.py` file, which is called when installing the xApp, as stated in the xApp's `Dockerfile`.

Entry point definition of `setup.py`:

```python
entry_points={"console_scripts": ["run-xapp-entrypoint.py=src.main:launchXapp"]}
```

Dockerfile entry point call:

```dockerfile
CMD run-xapp-entrypoint.py
```

The `launchXapp` function instantiates the xApp class and then calls its `start` method.
Both are implemented by the xApp's developer.

`launchXapp` definition:

```python
def launchXapp():
    xapp_instance = XappLogSdlRest() # Instantiating our custom xApp 
    xapp_instance.start() # Starting our custom xApp in threaded mode
```

Every xApp in this workshop has its class implemented in the `src/custom_xapp.py` file.
The custom xApps are written using OSC's [ricxappframe](https://pypi.org/project/ricxappframe/) package, which provides an implementation of the basic behaviors of an xApp to facilitate the xApp development process.
Inside the package files, the `ricxappframe/xapp_frame.py` library contains classes that a custom xApp will use as API for interacting with the SDL, sending and receiving RIC Message Router (RMR) messages, and other basic xApp functions.

There are three xApp classes in the framework: `_BaseXapp`, `Xapp`, and `RMRXapp`.

`_BaseXapp` is an abstract class from which `Xapp` and `RMRXapp` inherit functions common to every xApp.

`Xapp` is a class for general-purpose xApps, which does not add anything to the already inherited `_BaseXapp` methods as it assumes the developer will implement the xApp cycle.

On the other side, the `RMRXapp` class implements a loop that checks for received RMR messages and config-file changes, triggering handlers registered to these events.
Every xApp written using the `RMRXapp` class can only be reactive (i.e. acting only if some event occurs), while those written with `Xapp` can be both reactive and active (executing an entirely custom internal logic).

## _BaseXapp abstract class

The `_BaseXapp` class defines some important functions common to both `Xapp` and `RMRXapp`:
- `__init__`: initiates the xApp structure - instantiates an SDL wrapper and a logger; starts a threaded loop for managing RMR messages; sets an [inotify](https://pypi.org/project/inotify-simple/) watch to check for updates in the xApp's config-file, whose location is obtained by accessing the `CONFIG_FILE_PATH` environmental variable; registers the xApp in the Application Manager (AppMgr) via a threaded HTTP POST; and, at last, executes a `post_init` function if any is given
- `stop`: deregisters the xApp from the AppMgr and terminates the RMR thread
- `config_check`: returns the list of events detected by the config-file inotify watcher
- `healthcheck`: checks the RMR loop and the SDL health and returns `True` if both are healthy

## Xapp class

The `Xapp` class is instantiable and represents a general-use xApp, adding almost no function to its parent `_BaseXapp` class.
When instantiated, the `Xapp` requires an `entrypoint`: a function that will be called when the `run` method is executed.
Also, no `post_init` procedure can be executed for the `Xapp` class, since it is not present as an `__init__` parameter.
The only two `Xapp` functions, besides the ones inherited from `_BaseXapp` are:
- `__init__`: calls `_BaseXapp` initializer, then sets up the given `entrypoint` function
- `run`: calls the given `entrypoint`

An example of instantiating, running and stopping an `Xapp`:

```python
xapp = Xapp(
    entrypoint=my_entrypoint, # Function implemented by the developer 
    rmr_port=4560, # RMR data port
    rmr_wait_for_ready=True, # Blocks xApp initiation until RMR is ready
    use_fake_sdl=False # Use a fake in-memory SDL
)

xapp.run() # Calls my_entrypoint()

xapp.stop() # Deregisters the xApp and stops the RMR loop
```

It is important to notice that, if `my_entrypoint` does not start the xApp loop as a thread, it blocks the `xapp.stop()` of executing.
Therefore, it is always recommended to start the xApp loop in the entrypoint as a thread.

## RMRXapp class

The `RMRXapp` class is instantiable and represents a reactive xApp, restricting its behavior to executing handlers for two events: incoming RMR messages and config-file changes.
Additionally, the xApp developer can implement a threaded REST server instantiated at the `post_init` function for the xApp to also react to receiving HTTP messages.

When we call the `run` method of an `RMRXapp`, it starts a loop that polls for RMR messages and config-file changes while the flag `_keep_going` is `True`.
This flag is only set as `False` during the xApp termination when the `stop` method is called.

The `RMRXapp` works by calling handlers (or callbacks) for events of detecting config-file changes or receiving an RMR message.

When the `RMRXapp` loop detects a change in the config-file (via `inotify`), it calls `config_handler(data)`, passing a dictionary with the config-file content as `data`.
If no `config_handler` is passed in the `RMRXapp` instantiation, it uses a default handler that simply logs "xapp_frame: default config handler invoked".

For handling received RMR messages, a `_dispatch` variable contains a dictionary storing entries in the format of `RMR_MESSAGE_TYPE: handler_function`.
When the `RMRXapp` loop detects a received RMR message, it gets the RMR message type (an integer) and triggers the respective handler registered in `_dispatch`.
If no handler is registered for the message type, the `default_handler` is called.
The `default_handler` is obligatorily passed in the `RMRXapp` initialization.

The `RMRXapp` class `__init__` function calls the `_BaseXapp` initializer, then it:
- Sets up the given `default_handler` and `config_handler`
- Creates `_dispatch` as an empty dictionary
- Sets the flag `_keep_going` as `True`
- Registers a handler to respond RMR health check requisitions by checking if the RMR and SDL are working
- If no `config_handler` is provided, set up a handler that logs "xapp_frame: default config handler invoked"
- Calls the config-handler at the end of initialization

The other `RMRXapp` methods are: 
- `register_callback`: registers a handler to a given RMR message type (an integer), overwriting the previous handler if there is any
- `run`: starts the `RMRXapp` loop (in threaded mode if the `thread` parameter is set as `True`) that repeats while `_keep_going` is `True`
- `stop`: calls the `_BaseXapp` `stop` method, then sets `_keep_going` as `False`

An example of instantiating, running, and stopping an `RMRXapp`:

```python
rmr_xapp = RMRXapp(
    default_handler=my_default_handler, # Handler for unregistered RMR messages (implemented by the developer)
    config_handler=my_config_handler, # Handler for config-file changes (implemented by the developer)
    rmr_port=4560, # RMR data port
    post_init=my_post_init, # Function called during xApp startup (implemented by the developer)
    use_fake_sdl=False # Use a fake in-memory SDL
)

rmr_xapp.run(
    thread=True, # Starts the RMRXapp loop as a thread
    rmr_timeout=5, # Seconds to wait for RMR messages to arrive
    inotify_timeout=0 # Seconds to wait for an inotify event to arrive from the config-file watcher
)

rmr_xapp.stop() # Deregisters the xApp, stops the RMR loop and stops the RMRXapp loop
```

The figure below illustrates the differences between `Xapp` and `RMRXapp` classes:

![xApp deployment](/figs/workshop_ricxappframe_classes_startup.png)

## Custom xApp class

We define the logic of our xApp into a custom xApp class that does not need to inherit from any other class.

In our example xApp `xapp2logsdlrest`, the `src/main.py` launches the xApp by instantiating the custom xApp class `XappLogSdlRest` and executing its `start` method.
The `XappLogSdlRest` class is written in `src/custom_xapp.py`.
It is not a reactive xApp, since it just loops every second logging a message.
Therefore, `Xapp` is used as the xApp framework class.

We describe the `XappLogSdlRest` initialization below:
1. When we instantiate `XappLogSdlRest`, it sets up an independent logger, different from the `Xapp` instance logger (used by the internal framework functions).
2. Then, we instantiate `Xapp` passing our `_entrypoint` function as a parameter.
The `Xapp` instantiation already registers the xApp on AppMgr and catches the config-file data.
3. After this, we use the `signal` library to register `_handle_signal` as a handler function to be called when `SIGTERM`, `SIGQUIT`, or `SIGINT` are received.
4. We set some flags to control the xApp execution.
5. An HTTP server is started to listen for any message at port `8080`
6. Lastly, we indicate the xApp is ready by setting the `_ready` flag as `True` 

The signal handling is mainly important to gracefully terminate the xApp when we uninstall it with `dms_cli uninstall`.
This triggers the Kubernetes to undeploy the xApp pod, which enters the `Terminating` state and receives a `SIGTERM` signal.
This signal is handled by the xApp by triggering the xApp shutdown. 
Additionally, `SIGQUIT` and `SIGINT`, for quitting or interrupting the pod, trigger the same handler.

One important aspect of signal handling is that it can only be called if the xApp is executing in threaded mode.
Otherwise, the handler will not be called, since the `RMRXapp` loop blocks it.

The figure below illustrates the flow of a custom xApp:

![xApp deployment](/figs/workshop_custom_xapp_flow.png)

Besides `__init__`, the `XappLogSdlRest` has other eight functions:
- `_entrypoint`: contains the xApp logic that will be executed when the `Xapp` class `run` method is called
- `_loop`: called by `_entrypoint` to log how many loops it did while the `_shutdown` flag is `False`
- `start`: called by the `src/main.py` to start the xApp execution by running the `Xapp` class `run` method
- `stop`: sets the `_shutdown` flag to `True` to interrupt the `_loop` and calls the `Xapp` class `stop` method
- `_handle_signal`: execute the `stop` function when `SIGTERM`, `SIGQUIT`, or `SIGINT` are received
- `config_handler`: handler to respond HTTP GET messages at the URI path `ric/v1/config` by sending the serialized config-file JSON
- `liveness_handler`: handler to respond HTTP GET messages at the URI path `ric/v1/health/alive` by sending a serialized JSON that indicates the result of the `health_check` method from the `_BaseXapp` class
- `readiness_handler`: handler to respond HTTP GET messages at the URI path `ric/v1/health/ready` by sending a serialized JSON that indicates if the xApp is ready

# Logging with `mdclogpy`

OSC provides a Mapped Diagnostic Context (MDC) logging library called `mdclogpy`.

To log messages, we instantiate a `Logger` object and call its `debug`, `info`, `warning`, or `error` methods.
Each method represents a message logging level, following the hierarchy: DEBUG < INFO < WARNING < ERROR.
We set the log level with `set_level`.

For example:

```python
from mdclogpy import Logger, Level
logger = Logger()
logger.set_level(Level.INFO)
logger.error("This is a log at the ERROR level")
logger.warning("This is a log at the WARNING level")
logger.info("This is a log at the INFO level")
logger.debug("This is a log at the DEBUG level")
```

The code above will log the ERROR, WARNING, and INFO messages, but not the DEBUG one, because the logging level is set as INFO.
When instantiating the logger, the log level can also be passed as a parameter.

A log message is a JSON with the fields:
- `"ts"`: the timestamp of the log in Unix time
- `"crit"`: the log level of severity
- `"id"`: the logger name
- `"mdc"`: an object containing all existing key-value pairs of the MDC (e.g. the pod and service name)
- `"msg"`: the message logged

Although the `mdclogpy` library has functions to fully customize the MDC, it also provides a `get_env_params_values` method to generate an MDC with the process ID and the values of the environmental variables `SYSTEM_NAME`, `HOST_NAME`, `SERVICE_NAME`, `CONTAINER_NAME`, and `POD_NAME`.
However, to make the logs visually cleaner while streaming the instructor's screen during this workshop, the xApps in this workshop do not generate MDCs.

------------------------------------------------------------------------ **EXERCISE 1** ------------------------------------------------------------------------

Open a Python3 terminal (use the `python3` command) and:
- Instantiate a logger with the name `logger_test` at the `WARNING` level
- Get the environment parameter values
- Log an `ERROR` message
- Log a `WARNING` message
- Log a `INFO` message
- Change the log level to `DEBUG`
- Log a `DEBUG` message

<p>
<details>
<summary>Solution</summary>

Inside the Python terminal, execute:

```python
from mdclogpy import Logger, Level
logger = Logger(name="logger_test", level=Level.WARNING)
logger.get_env_params_values()
logger.error("This is a log at the ERROR level")
logger.warning("This is a log at the WARNING level")
logger.info("This is a log at the INFO level")
logger.set_level(Level.DEBUG)
logger.debug("This is a log at the DEBUG level")
```

The results should be similar to:

```json
{"ts": 1714707977986, "crit": "ERROR", "id": "logger_test", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 347478}, "msg": "This is a log at the ERROR level"}
{"ts": 1714707995394, "crit": "WARNING", "id": "logger_test", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 347478}, "msg": "This is a log at the WARNING level"}
{"ts": 1714708009564, "crit": "DEBUG", "id": "logger_test", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 347478}, "msg": "This is a log at the DEBUG level"}
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 2** ------------------------------------------------------------------------

Edit the xApp code to log the xApp config-file as an `INFO` message at the beginning of the `entrypoint` function, before starting the `_loop` thread.
The config-file is accessible as the `_config_data` attribute (created by the `_BaseXapp` class).

After editing the entrypoint, install the `xapp2logsdlrest` by running:

```bash
bash update_xapp.sh
```

This script onboards, builds, pushes, and installs the new xApp, uninstalling any previous one with the same name.

To view the logs, run:

```bash
bash log_xapp.sh
```

<p>
<details>
<summary>Solution</summary>

Edit the `_entrypoint` function located in the `src/custom_xapp.py` file to:

```python
def _entrypoint(self, xapp:Xapp):
    """
    Function containing the xApp logic. Called by the xApp framework object when it executes its run() method.
    
    Parameters
    ----------
    xapp: Xapp
        This is the xApp framework object (passed by the framework).
    """         
    
    # Logging the config file
    self.logger.info("Config file:" + str(self._xapp._config_data))
    
    # Starting the xApp loop
    self.logger.info("Starting xApp loop in threaded mode.")
    Thread(target=self._loop).start()
```

The config-file log should be similar to:

```json
{"ts": 1715669020689, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": "Config file:{'name': 'xapp2logsdlrest', 'version': '1.0.0', 'containers': [{'image': {'name': 'xapp2logsdlrest', 'registry': '127.0.0.1:5001', 'tag': '1.0.0'}, 'name': 'xapp2logsdlrestcontainer'}], 'messaging': {'ports': [{'container': 'xapp2logsdlrestcontainer', 'description': 'http service', 'name': 'http', 'port': 8080}, {'container': 'xapp2logsdlrestcontainer', 'description': 'rmr route port for bouncer xapp', 'name': 'rmrroute', 'port': 4561}, {'container': 'xapp2logsdlrestcontainer', 'description': 'rmr data port', 'name': 'rmrdata', 'policies': [1], 'port': 4560, 'rxMessages': ['RIC_SUB_RESP', 'RIC_INDICATION', 'RIC_SUB_DEL_RESP'], 'txMessages': ['RIC_SUB_REQ', 'RIC_SUB_DEL_REQ']}]}, 'readinessProbe': {'httpGet': {'path': 'ric/v1/health/ready', 'port': 8080}, 'initialDelaySeconds': 5, 'periodSeconds': 15}, 'livenessProbe': {'httpGet': {'path': 'ric/v1/health/alive', 'port': 8080}, 'initialDelaySeconds': 5, 'periodSeconds': 15}}"}
```

</details>
</p>

# Interacting with the SDL

The OSC Near-RT RIC Kubernetes cluster has a Database as a Service (DBaaS) pod running a [Redis](https://redis.io/) key-value database.

The SDL abstracts access to the distributed database by providing a lightweight API, which is used by the `SDLWrapper` class, instantiated during the `_BaseXapp` initialization.

When instantiating `Xapp` or `RMRXapp` classes, the `use_fake_sdl` flag determines if a local in-memory database is used instead of accessing the DBaaS pod, providing a safe temporary environment for xApp testing.

The SDL relies on two main environment variables to connect to the DBaaS:
- `DBAAS_SERVICE_HOST`: the service name, usually `service-ricplt-dbaas-tcp.ricplt`
- `DBAAS_SERVICE_PORT`: the service port, usually `6379`

To identify data, the SDL needs two strings: a **key** and a **SDL namespace**.
That way, we can group keys by namespace.
For example, every key from the `xapp2logsdlrest` xApp could be at the `xapp2logsdlrest` namespace.
By standard, the `SDLWrapper` serializes data before storing and deserializes data after retrieving it.
If you prefer not to serialize or deserialize data, you can set the `usemsgpack` to `False` when calling SDL functions.

The `_BaseXapp` provides four SDL functions that use the `SDLWrapper` to interact with the SDL:

- `sdl_set`: stores a value for a given key and SDL namespace, overwriting any stored value
- `sdl_get`: given the key and SDL namespace, returns the value or `None` if not found
- `sdl_find_and_get`: given the SDL namespace and a key prefix, returns a dictionary of all key-value pairs where the key matches the prefix 
- `sdl_delete`: given the key and SDL namespace, deletes the respective key-value pair

------------------------------------------------------------------------ **EXERCISE 3** ------------------------------------------------------------------------

Rewrite the entire `while` block in the `_loop` function following the directions below:
- At the `xapp2logsdlrest` SDL namespace, maintain an `xapp-loops` key updated with the number of times the xApp looped
- When the number of loops reaches 30, delete the `xapp-loops` key from the SDL
- At the `xapp2logsdlrest` SDL namespace, maintain an `xapp-deletes` key updated with the number of times the `xapp-loops` was deleted
- After updating `xapp-loops` and `xapp-deletes`, log an `INFO` message with a dictionary containing both key-value pairs
- Sleep for 1 second after each loop

Then, install the `xapp2logsdlrest` by running:

```bash
bash update_xapp.sh
```

To view the logs, run:

```bash
bash log_xapp.sh
```

Wait 30 seconds and execute `update_xapp.sh` and `log_xapp.sh` again.
Repeat this process one more time.

<p>
<details>
<summary>Solution</summary>

Edit the `_loop` function located in the `src/custom_xapp.py` file to:

```python
def _loop(self):
    """
    Loops logging an increasing counter each second.
    """    
    while not self._shutdown: # True since custom xApp initialization until stop() is called
        n_loops = self._xapp.sdl_get(namespace="xapp2logsdlrest", key="xapp-loops")
        if n_loops is None:
            n_loops = 0
        n_loops += 1
        self._xapp.sdl_set(namespace="xapp2logsdlrest", key="xapp-loops", value=n_loops)
        if n_loops >= 30:
            self._xapp.sdl_delete(namespace="xapp2logsdlrest", key="xapp-loops")
            n_resets = self._xapp.sdl_get(namespace="xapp2logsdlrest", key="xapp-deletes")
            if n_resets is None:
                n_resets = 0
            self._xapp.sdl_set(namespace="xapp2logsdlrest", key="xapp-deletes", value=n_resets+1)
        self.logger.info(self._xapp.sdl_find_and_get(namespace="xapp2logsdlrest", prefix="xapp"))
        sleep(1) # Sleep for 1 second
```

The `sdl_find_and_get` logs should be similar to:

```json
{"ts": 1714715802165, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-loops": 1}}
{"ts": 1714715803170, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-loops": 2}}
...
{"ts": 1714716330927, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-loops": 29}}
{"ts": 1714716331932, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": 1}}
{"ts": 1714716332936, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": 1, "xapp-loops": 1}}
{"ts": 1714716333942, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": 1, "xapp-loops": 2}}
...

```

</details>
</p>

# Implementing HTTP REST communication

As part of the `ricxappframe` package, OSC's Python xApp framework provides an `xapp_rest` library implementing an HTTP server for REST communication.
This library is based on the Python [http](https://docs.python.org/3/library/http.html) package (specifically `http.server`) and assumes that the server must run as a thread.
The only requirement to use the `xapp_rest` HTTP server is specifying the `http` port in the config-file for the http service to be created during the xApp installation.

## HTTP server

To create the HTTP server, a listening address must be informed.
For example, an HTTP server that listens to any host at the default HTTP port (8080) can be instantiated by executing:

```python
http_server = xapp_rest.ThreadedHTTPServer("0.0.0.0", 8080)
```

Then, we register handlers to be called when an HTTP message is received.
Every handler is registered with a unique name (used as an identifier) an HTTP method (only `GET`, `POST`, and `DELETE` are accepted), a URI path, and a callback function.
Below we register a handler identified as `"my_handler"` that executes the `my_handler` function when an HTTP GET message is received in the URI path `"/ric/v1/my_path"`: 

```python
http_server.handler.add_handler(http_server.handler, method="GET", name="my_handler", uri="/ric/v1/my_path", callback=my_handler)
```

When invoking the callback function, the HTTP server passes four parameters, in this exact order:
1. `name`: a string with the name of the registered handler 
2. `path`: a string with the URI path of the HTTP request 
3. `data`: a bytes object with the encoded payload (need to be converted to a string using `data.decode()`)
4. `ctype`: a string with the content type of the HTTP request

The callback must also return a response: a dictionary with information for the server to construct an HTTP response and send it to the client.
The `xapp_rest` provides an `initResponse` function to generate this dictionary.
The `initResponse` method has two optional parameters for initiating the dictionary with some data: `status` is an integer with the HTTP status code and `response` is a string with the HTTP response text.
Other pieces of information, like a JSON payload, must be written directly on the response dictionary.

For example, we define below a simple handler callback function that responds with a `200 OK` HTTP status and, as payload, a `{"my_key":"my_value"}` dictionary:

```python
def my_handler(self, name:str, path:str, data:bytes, ctype:str):
    response = xapp_rest.initResponse(status=200, response="My_response_name")
    response['payload'] = json.dumps({"my_key": "my_value"})
    return response
```

Printing the `response` dictionary will output:

```python
{
  "response": "My_response_name",
  "status": 200,
  "payload": "{\"my_key\": \"my_value\"}",
  "ctype": "application/json",
  "attachment": None,
  "mode": "plain"
}
```

The `"attachment"` value can contain a filename for the HTTP client to store the payload, while the `"mode"` value contains the payload mode (`plain` for UTF-8 text or `binary` for bytes object).

With the HTTP server instantiated and the handlers registered, we finally run the server thread:

```python
http_server.start()
```

To stop the server (for example, during the xApp termination), we execute:

```python
self.http_server.stop()
```

## HTTP requests

Besides handling HTTP messages with a server, we may as well want to communicate via HTTP REST by sending HTTP requests.
To achieve this, we use the Python [requests](https://pypi.org/project/requests/) package, which simplifies sending an HTTP request into a single function.
As a usage example, the xApp registration is implemented in the `_BaseXapp` class as a `requests.post` method sending a JSON payload to the AppMgr as below:

```python
resp = requests.post(request_url, json=msg)
self.logger.debug("Post to '{}' done, status : {}".format(request_url, resp.status_code))
self.logger.debug("Response Text : {}".format(resp.text))
```

Similarly, we can send an HTTP GET request to AppMgr's HTTP service at the URI path `ric/v1/xapps` to get the list of registered xApps:

```python
resp = requests.get("http://service-ricplt-appmgr-http.ricplt:8080/ric/v1/xapps")
self.logger.info("AppMgr responded with status {}".format(resp.status_code))
self.logger.info("Registered xApps list: {}".format(resp.json()))
```

------------------------------------------------------------------------ **EXERCISE 4** ------------------------------------------------------------------------

Modify the xApp `_entrypoint` function to get and log the list of registered xApps from the AppMgr when the xApp starts running.
To do this, you must send an HTTP GET to the AppMgr HTTP service (at port 8080) with URI path `ric/v1/xapps`.
Tip: the full URL will be `"http://service-ricplt-appmgr-http.ricplt:8080/ric/v1/xapps"`.

<p>
<details>
<summary>Solution</summary>

The edited `_entrypoint` can be:

```python
def _entrypoint(self, xapp:Xapp):
    """
    Function containing the xApp logic. Called by the xApp framework object when it executes its run() method.

    Parameters
    ----------
    xapp: Xapp
        This is the xApp framework object (passed by the framework).
    """         

    # Logging the config file
    self.logger.info("Config file:" + str(self._xapp._config_data))

    # Logging the list of registered xApps (got from AppMgr)
    xapp_list = requests.get("http://service-ricplt-appmgr-http.ricplt:8080/ric/v1/xapps")
    self.logger.info("List of registered xApps: " + str(xapp_list.json()))
    
    # Starting the xApp loop
    self.logger.info("Starting xApp loop in threaded mode.")
    Thread(target=self._loop).start()
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 5** ------------------------------------------------------------------------

Write and register a handler for HTTP POST messages at URI path `ric/v1/reset_count` with payload `{"xapp-deletes": X}`, where `X` must be an integer.
The handler must log the received payload and store the `xapp-deletes` value in the SDL at key `xapp-deletes` and SDL namespace `xapp2logsdlrest`.

Then, update the xApp and check its logs.

```bash
bash update_xapp.sh
bash log_xapp.sh
```

Send an HTTP POST message to the xApp HTTP service using `curl`.
For example, this command will set the `xapp-deletes` to `-5`:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"xapp-deletes": -5}' http://$(kubectl get svc -n ricxapp -o wide | grep xapp2logsdlrest-http | awk '{print $3}'):8080/ric/v1/reset_count
```

At last, check the xApp logs for changes in the `xapp-deletes` SDL value.

```bash
bash log_xapp.sh
```

<p>
<details>
<summary>Solution</summary>

In the `__init__` function, register the handler with:

```python
self.http_server.handler.add_handler(self.http_server.handler, method="POST", name="sdl_delete", uri="/ric/v1/reset_count", callback=self.sdl_delete_handler)
```

Also, write the handler function as a method of `XappLogSdlRest`:

```python
def sdl_delete_handler(self, name:str, path:str, data:bytes, ctype:str):
    """
    Handler for the HTTP POST /ric/v1/reset_count request.
    """
    self.logger.info("Received POST /ric/v1/reset_count request with content type {}.".format(ctype))
    data_dict = json.loads(data)
    self.logger.debug("Received payload {}".format(data_dict))
    self._xapp.sdl_set(namespace="xapp2logsdlrest", key="xapp-deletes", value=data_dict["xapp-deletes"])
    response = xapp_rest.initResponse(
        status=200, # Status = 200 OK
        response="SDL delete"
    )
    return response
```

Update the xApp, send the HTTP POST and get the xApp logs:
```bash
bash update_xapp.sh
curl -X POST -H "Content-Type: application/json" -d '{"xapp-deletes": -5}' http://$(kubectl get svc -n ricxapp -o wide | grep xapp2logsdlrest-http | awk '{print $3}'):8080/ric/v1/reset_count
bash log_xapp.sh
```

The logs should be similar to:

```json
{"ts": 1715747238816, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": 11, "xapp-loops": 23}}
{"ts": 1715747239820, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": 11, "xapp-loops": 24}}
{"ts": 1715747239995, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": "Received POST /ric/v1/reset_count request with content type application/json."}
{"ts": 1715747239995, "crit": "DEBUG", "id": "XappLogSdlRest", "mdc": {}, "msg": "Received payload {'xapp-deletes': -5}"}
{'response': 'SDL delete', 'status': 200, 'payload': None, 'ctype': 'application/json', 'attachment': None, 'mode': 'plain'}
10.244.0.1 - - [15/May/2024 04:27:19] "POST /ric/v1/reset_count HTTP/1.1" 200 -
{"ts": 1715747240824, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": -5, "xapp-loops": 25}}
{"ts": 1715747241828, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": -5, "xapp-loops": 26}}
{"ts": 1715747242833, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": -5, "xapp-loops": 27}}
{"ts": 1715747243839, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": -5, "xapp-loops": 28}}
{"ts": 1715747244842, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": -5, "xapp-loops": 29}}
{"ts": 1715747245844, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": {"xapp-deletes": -4}}
```

</details>
</p>

## Main xApp HTTP REST interaction

This subsection covers the main HTTP REST interactions of an xApp.
All of them are already implemented in `xapp2logsdlrest`.
They are:
- Sending xApp registration and deregistration requests
- Handling config-file requests
- Handling Kubernetes liveness and readiness probes

### xApp registration and deregistration

The AppMgr is responsible for managing the xApp lifecycle.
It accounts for running xApps by maintaining a list of registered xApps.
For example, when the AppMgr registers or deregisters an xApp, it sends the list of all registered xApps to the Routing Manager (RtMgr), which distributes updated routes for all xApps and RIC components.

The AppMgr updates the list of registered xApps when it receives a registration or deregistration request from an xApp, which are HTTP messages carrying a JSON with xApp data.
Also, both are already implemented in OSC's Python xApp framework `_BaseXapp` class, so xApps written using either `Xapp` or `RMRXapp` classes do not need to re-implement them.

The registration request is an HTTP POST sent by the xApp to the AppMgr during the `_BaseXapp` initialization (called during `Xapp` and `RMRXapp` initializations).
The message is sent to the AppMgr `http` service at port `8080` and path `ric/v1/register`.
Thus, as the AppMgr is deployed at the `ricplt` namespace, the full URL is: `http://service-ricplt-appmgr-http.ricplt:8080/ric/v1/register`.

The `_BaseXapp` class constructs the registration JSON message with the fields below:
- `"appName"`: `HOSTNAME` environmental variable, usually set as the config-file `name` value
- `"appInstanceName"`: `name` value from xApp's config-file
- `"appVersion"`: `version` value from xApp's config-file
- `"configPath"`: should be the HTTP path for requesting the xApp config-file JSON, but it is always set as empty (`""`), so the AppMgr assumes the standard path `ric/v1/config`
- `"httpEndpoint"`: the `http` service endpoint, formatted as `<HTTP_SERVICE_IP>:<HTTP_SERVICE_PORT>`
- `"rmrEndpoint"`: the `rmrdata` (not `rmrroute`) service endpoint, formatted as `<RMR_SERVICE_IP>:<RMR_DATA_SERVICE_PORT>`
- `"config"`: the **dumped** config file JSON, which **will be serialized again** after dumping the registration request JSON

If the `config` field is not filled in, the AppMgr sends a config-file request (described in the next subsection) at the `configPath` URI path.

The deregistration request is an HTTP POST sent by the xApp to the AppMgr during the xApp termination when the `stop` method from `_BaseXapp` class is called.
The message is sent to the AppMgr `http` service at port `8080` and URI path `ric/v1/deregister`.
So, as the AppMgr is deployed at the `ricplt` namespace, the full URL is: `http://service-ricplt-appmgr-http.ricplt:8080/ric/v1/deregister`.
The `_BaseXapp` class constructs the registration JSON message with the fields below:
- `"appName"`: `HOSTNAME` environmental variable, usually set as the config-file `name` value
- `"appInstanceName"`: `name` value from xApp's config-file

### Config-file requests

The main reason for config-file requests is if the AppMgr did not receive the xApp config-file in the registration request.
In this case, the AppMgr sends an HTTP GET to `httpEndpoint` at the URI path `configPath`, where `httpEndpoing` and `configPath` are indicated in the registration request.
In case of `configPath` being empty, the AppMgr assumes `ric/v1/config` as the default path to sending the config-file request.

The response sent by the xApp must have the serialized config-file JSON as payload.

------------------------------------------------------------------------ **EXERCISE 6** ------------------------------------------------------------------------
Check the config-file of the `xapp2logsdlrest` xApp using the `curl` command.
By default, the `curl` command sends an HTTP GET if no HTTP method is specified.

<p>
<details>
<summary>Solution</summary>

We send an HTTP GET to the `xapp2logsdlrest` HTTP service (at port 8080) for the URI paths `ric/v1/health/alive` and `ric/v1/health/ready`.
The command below automates the `kubectl get svc` command to consult the xApp service's IP.
The `jq` receives the config-file JSON in a single line and outputs it with line breaks and indentation.

```bash
curl http://$(kubectl get svc -n ricxapp -o wide | grep xapp2logsdlrest-http | awk '{print $3}'):8080/ric/v1/config | jq
```

The ouput should be:

```json
{
    "containers" : [
        {
            "image" : {
                "name" : "xapp2logsdlrest",
                "registry" : "127.0.0.1:5001",
                "tag" : "1.0.0"
            },
            "name" : "xapp2logsdlrestcontainer"
        }
    ],
    "livenessProbe" : {
        "httpGet" : {
            "path" : "ric/v1/health/alive",
            "port" : 8080
        },
        "initialDelaySeconds" : 5,
        "periodSeconds" : 15
    },
    "messaging" : {
        "ports" : [
            {
                "container" : "xapp2logsdlrestcontainer",
                "description" : "http service",
                "name" : "http",
                "port" : 8080
            },
            {
                "container" : "xapp2logsdlrestcontainer",
                "description" : "rmr route port for bouncer xapp",
                "name" : "rmrroute",
                "port" : 4561
            },
            {
                "container" : "xapp2logsdlrestcontainer",
                "description" : "rmr data port",
                "name" : "rmrdata",
                "policies" : [
                    1
                ],
                "port" : 4560,
                "rxMessages" : [
                    "RIC_SUB_RESP",
                    "RIC_INDICATION",
                    "RIC_SUB_DEL_RESP"
                ],
                "txMessages" : [
                    "RIC_SUB_REQ",
                    "RIC_SUB_DEL_REQ"
                ]
            }
        ]
    },
    "name" : "xapp2logsdlrest",
    "readinessProbe" : {
        "httpGet" : {
            "path" : "ric/v1/health/ready",
            "port" : 8080
        },
        "initialDelaySeconds" : 5,
        "periodSeconds" : 15
    },
    "version" : "1.0.0"
}
```

</details>
</p>

### Liveness and readiness probes

Kubernetes uses HTTP GET messages to send probes checking the pod health according to the pod's logic.
The liveness probe is used to check if the pod is healthy, while the readiness probe checks if the pod is ready to start. 
Both liveness and readiness probes should be configured in the config-file (as objects at the same level of `name`, `version`, `containers`, and `messaging`).

The JSON object in the config-file must define, for both probes:
- `"httpGet"`: an object with `"path"` and `"port"` containing a string for the URI path and an integer for the HTTP port, respectively 
- `"initialDelaySeconds"`: an integer with the number of seconds that should be waited after the xApp installation to send the first liveness probe
- `"periodSeconds"`: an integer with the number of seconds that should be waited to resend the liveness probe

Below we have examples for the config-file JSON object defining liveness and readiness probes:

```json
"livenessProbe": {
    "httpGet": {
        "path": "ric/v1/health/alive",
        "port": 8080
    },
    "initialDelaySeconds": 5,
    "periodSeconds": 15
}
```

```json
"readinessProbe": {
    "httpGet": {
        "path": "ric/v1/health/ready",
        "port": 8080
    },
    "initialDelaySeconds": 5,
    "periodSeconds": 15
}
```

------------------------------------------------------------------------ **EXERCISE 7** ------------------------------------------------------------------------
Check the readiness and liveness of the `xapp2logsdlrest` xApp using the `curl` command.
By default, the `curl` command sends an HTTP GET if no HTTP method is specified.

<p>
<details>
<summary>Solution</summary>

We send an HTTP GET to the `xapp2logsdlrest` HTTP service (at port 8080) for the URI paths `ric/v1/health/alive` and `ric/v1/health/ready`.

```bash
curl $(kubectl get svc -n ricxapp -o wide | grep xapp2logsdlrest-http | awk '{print $3}'):8080/ric/v1/health/alive
curl $(kubectl get svc -n ricxapp -o wide | grep xapp2logsdlrest-http | awk '{print $3}'):8080/ric/v1/health/ready
```

The output should be:

```json
{"status": "Healthy"}
{"status": "Ready"}
```

</details>
</p>
