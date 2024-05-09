# Class 2: xApp overview, logging, SDL, and REST
At the end of this class, you should be able to:
- Understand the structure of an xApp written using OSC's Python xApp Framework
- Log messages from the xApp using OSC's `mdclogpy` library
- Create, retrieve, update, and delete data using the Shared Data Layer (SDL) API
- Develop REST interaction (as server and cliente) for the xApp

All exercises in this class refer to the `xapp2logsdlrest` xApp, located in `xapp-workshop/exercise-xapps/xapp-2-log-sdl-rest` folder. It is highly advisable to change the current directory to the xApp directory as every command assumes that it is the actual directory.

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

The `launchXapp` function instantiates the xApp class then calls its `start` method.
Both are implemented by the xApp's developer.

`launchXapp` definition:

```python
def launchXapp():
    xapp_instance = XappLogSdlRest() # Instantiating our custom xApp 
    xapp_instance.start() # Starting our custom xApp in threaded mode
```

Every xApp in this workshop has its class implemented in the `src/custom_xapp.py` file.
The custom xApps are written using the `ricxappframe` library, which provides an implementation of the basic behaviours of an xApp to facilitate the xApp development process.
Inside the library files, the `ricxappframe/xapp_frame.py` contains classes that a custom xApp will use as API for interacting with the SDL, managing RIC Message Router (RMR) messages, and other basic xApp functions.

There are three xApp classes in the framework: `_BaseXapp`, `Xapp`, and `RMRXapp`.
`_BaseXapp` is an abstract class from which `Xapp` and `RMRXapp` inherit functions commom to every xApp.
`Xapp` is a class for geneneral purpose xApps, which does not add anything to the already inherited `_BaseXapp` methods as it assumes the developer will implement the xApp cycle.
On the other side, the `RMRXapp` class implements a loop that checks for received RMR messages and config-file changes, triggering handlers registered to these events.
xApps written using the `RMRXapp` class can only be reactive (i.e. acting only if some event occurs), while those written with `Xapp` can be both reactive and active (executing an entirely custom internal logic).

## _BaseXapp abstract class

The `_BaseXapp` class defines some important functions that will be executed in this class:
- `__init__`: initiates the xApp structure: instantiates an SDL wrapper and a logger; starts a thread to receive RMR messages; sets an inotify watch to check for updates in the xApp's config-file, whose location is obtained by accessing the `CONFIG_FILE_PATH` environmental variable; registers the xApp in the Application Manager (AppMgr) via a threaded HTTP REST Post; and, at last, executes a `post_init` function if any is given.
- `stop`: deregisters the xApp from the AppMgr and terminates the RMR thread. 
- `config_check`: returns the list of events detected by the config-file inotify watcher.

## Xapp class

The `Xapp` class is instatiable and represents a general use xApp, adding basically nothing to its parent `_BaseXapp` class.
When instantiated, the `Xapp` requires an `entrypoint`: a function that will be called when the `run` method is executed.
Also, no `post_init` procedure can be executed for the `Xapp` class, since it is not present as an `__init__` parameter.
The only two `Xapp` functions, besides the ones inherited from `_BaseXapp` are:
- `__init__`: calls `_BaseXapp` initializer, then sets up the given `entrypoint` function
- `run`: calls the stored `entrypoint`

## RMRXapp class

The `RMRXapp` class is instantiable and represents a reactive xApp, restricting its behaviour to executing handlers for two events: incoming RMR messages and config-file changes.
When running an `RMRXapp`, it loops polling for RMR messages and config-file changes while the flag `_keep_going` is `True`.
This flag is only set as `False` during the xApp termination, by calling the `stop` method.

As the RMRXapp only reacts to config-file changes and RMR messages , there are special handlers for both.
First, when the `RMRXapp` loop detects a change in the config-file via `inotify`, it calls `config_handler(data)`, passing the deserialized config-file JSON as `data`.
If no `config_handler` is passed in the `RMRXapp` instantiation, it generates a default one that simply logs "xapp_frame: default config handler invoked".
For handling RMR messages, a `_dispatch` variable contains a dictionary storing entries in the format of `RMR_MESSAGE_TYPE: handler_function`.
When the `RMRXapp` loop detects a received RMR message, it gets the message type (a number) and triggers the respective handler registered in `_dispatch`.
If no handler is registered for the message type, the `default_handler` is called.
The `default_handler` is obligatorilly passed in the `RMRXapp` initialization.
Every handler, including the `default_handler`, must have the format of 
A handler for RMR messages must have the format of `handler(summary, sbuf)` to be called by the `RMRXapp` loop, passing `sbuf` as the pointer to the RMR message buffer and `summary` as a dictionary for the RMR message data and metadata.

The `RMRXapp` class `__init__` function calls the `_BaseXapp` initializer, then it:
- Sets up the given `default_handler` and `config_handler`
- Creates `_dispatch` as an empty dictionary
- Sets the flag `_keep_going` as `True`
- Registers a handler to respond RMR health check requisitions by checking if the RMR and SDL are working
- If no `config_handler` is provided, sets up a handler that logs a "xapp_frame: default config handler invoked"
- Calls the config-handler at the end of initialization

The other `RMRXapp` methods are: 
- `register_callback`: registers a handler in the format of `handler(summary, sbuf)` to the given RMR message type (a number), overwriting any other handler for that message type
- `run`: starts the `RMRXapp` loop (in threaded mode if the `thread` parameter is set as `True`) that repeats while `_keep_going` is `True`
- `stop`: calls the `_BaseXapp` `stop` method, then sets `_keep_going` as `False`

## Custom xApp class

We define the logic of our xApp into a custom xApp class.
It does not need to inherit from any other class.
In our example xApp `xapp2logsdlrest`, the `src/main.py` launches the xApp by instantiating the `XappLogSdlRest` class and executing its `start` method.
The class itself is written in `src/custom_xapp.py`.
It is not a reactive xApp, since it just loops every second logging a message.
Therefore, `Xapp` is used as the xApp class from the framework.

When we instantiate `XappLogSdlRest`, it sets up an independent logger, different from the `Xapp` instance logger, which is called by the inner framework functions.
Then, we instantiate `Xapp` passing our `_entrypoint` function as a parameter.
The `Xapp` instantiation process already register the xApp on AppMgr and catches the config-file data.
After this, we use the `signal` library to register `_handle_signal` as a handler function to be called when `SIGTERM`, `SIGQUIT`, or `SIGINT` are received.
Those signals can be sent by Kubernetes to the pod to indicate that it must start a termination routine.
When we uninstall an xApp via `dms_cli uninstall`, the xApp pod enters the `Terminating` state and a `SIGTERM` signal is received.
One important aspect of signal handling is that it can only be called if the xApp is executing in threaded mode.
Otherwise, the handler will not be called.
Lastly, we set some flags to control the xApp execution.

Besides `__init__`, the `XappLogSdlRest` has five functions:
- `_entrypoint`: contains the xApp logic that will be executed when the `Xapp` class `run` method is called
- `_loop`: called by `_entrypoint` to logs how many loops it did while the `_shutdown` flag is `False`
- `start`: called by the `src/main.py` to start the xApp execution by running the `Xapp` class `run` method
- `stop`: sets the `_shutdown` flag to `True` to interrupt the `_loop` and calls the `Xapp` class `stop` method
- `_handle_signal`: execute the `stop` function when `SIGTERM`, `SIGQUIT`, or `SIGINT` are received

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
When instantiating the logger, the log level can be passed as a parameter.

A log message is a JSON with the fields:
- `"ts"`: the timestamp of the log in Unix time
- `"crit"`: the log level of severity
- `"id"`: the logger name
- `"mdc"`: an object containing all existing key-value pairs of the MDC (e.g. the pod and service name)
- `"msg"`: the message logged

Although the `mdclogpy` has functions to fully customize the MDC, it also provides a `get_env_params_values` method to generate an MDC with the process ID and the values of the environmental variables `SYSTEM_NAME`, `HOST_NAME`, `SERVICE_NAME`, `CONTAINER_NAME`, and `POD_NAME`.
To make the logs visually cleaner while streaming the instructor screen in this workshop, the example xApps do not generate MDCs.

------------------------------------------------------------------------ **EXERCISE 1** ------------------------------------------------------------------------

Open a Python3 terminal (use the `python3` command) and:
- Instantiate a logger with name `logger_test` at the `WARNING` level
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
logger = Logger(name="xapp_name", level=Level.WARNING)
logger.get_env_params_values()
logger.error("This is a log at the ERROR level")
logger.warning("This is a log at the WARNING level")
logger.info("This is a log at the INFO level")
logger.set_level(Level.DEBUG)
logger.debug("This is a log at the DEBUG level")
```

The results should be similar to:

```json
{"ts": 1714707977986, "crit": "ERROR", "id": "xapp_name", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 347478}, "msg": "This is a log at the ERROR level"}
{"ts": 1714707995394, "crit": "WARNING", "id": "xapp_name", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 347478}, "msg": "This is a log at the WARNING level"}
{"ts": 1714708009564, "crit": "DEBUG", "id": "xapp_name", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 347478}, "msg": "This is a log at the DEBUG level"}
```

</details>
</p>

------------------------------------------------------------------------ **EXERCISE 2** ------------------------------------------------------------------------

Edit the xApp cycle to log the xApp config-file as an `INFO` message at the beginning of the `_loop` function, before the `while` block.
The config-file is accessable as the `_config_data` attribute of the `_BaseXapp` class.
Then, install the `xapp2logsdlrest` by running:

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

Edit the `_loop` function located in the `src/custom_xapp.py` file to:

```python
def _loop(self):
    """
    Loops logging an increasing counter each second.
    """
    self.logger.info("Config file:" + str(self._xapp._config_data))
    i = 1 # How many times we looped
    while not self._shutdown: # True since custom xApp initialization until stop() is called
        self.logger.info("Looped {} times.".format(i))
        i+=1
        sleep(1) # Sleeps for 1 second
```

The config-file log should be similar to:

```json
{"ts": 1714715802163, "crit": "INFO", "id": "XappLogSdlRest", "mdc": {}, "msg": "Config file:{'name': 'xapp2logsdlrest', 'version': '1.0.0', 'containers': [{'image': {'name': 'xapp2logsdlrest', 'registry': '127.0.0.1:5001', 'tag': '1.0.0'}, 'name': 'xapp2logsdlrestcontainer'}], 'messaging': {'ports': [{'container': 'xapp2logsdlrestcontainer', 'description': 'http service', 'name': 'http', 'port': 8080}, {'container': 'xapp2logsdlrestcontainer', 'description': 'rmr route port for bouncer xapp', 'name': 'rmrroute', 'port': 4561}, {'container': 'xapp2logsdlrestcontainer', 'description': 'rmr data port', 'name': 'rmrdata', 'policies': [1], 'port': 4560, 'rxMessages': ['RIC_SUB_RESP', 'RIC_INDICATION', 'RIC_SUB_DEL_RESP'], 'txMessages': ['RIC_SUB_REQ', 'RIC_SUB_DEL_REQ']}]}}"}
```

</details>
</p>

# Interacting with the SDL

The OSC Near-RT RIC Kubernetes cluster has a Database as a Service (DBaaS) pod running a [Redis](https://redis.io/) key-value database.
The SDL abstracts the access to the database in a lightweight API, which is used by the `SDLWrapper` class, instantiated by the `_BaseXapp` initialization.
When instantiating the `Xapp` or `RMRXapp` classes, the `use_fake_sdl` flag determines if an in-memory database is used, instead of accessing the DBaaS pod, thus providing a safe temporary environment for xApp testing.

The SDL relies on two main environmental variables to connect to the DBaaS:
- `DBAAS_SERVICE_HOST`: the service name, usually `service-ricplt-dbaas-tcp.ricplt`
- `DBAAS_SERVICE_PORT`: the service port, usually `6379`

To identify data, the SDL uses two strings: a **key** and a **SDL namespace**.
That way, all keys used by an xApp can be grouped in same namespace, which could be the xApp name.
By standard, the `SDLWrapper` serializes data before storing or deserializes data after retrieving it.
If it is preferred to not serialize/deserialize data, the `usemsgpack` parameter can be set as `False` when calling SDL functions.

The `_BaseXapp` provides four SDL functions that simply call the `SDLWrapper`:

- `sdl_set`: stores a value for a given key and SDL namespace, overwriting any stored value
- `sdl_get`: given the key and SDL namespace, returns the value or `None` if not found
- `sdl_find_and_get`: given the SDL namespace and a key prefix, returns a dictionary of all key-value pairs where the key matches the prefix 
- `sdl_delete`: given the key and SDL namespace, deletes the respective key-value pair

------------------------------------------------------------------------ **EXERCISE 3** ------------------------------------------------------------------------

Rewrite the entire `while` block at the `_loop` function following the directions below:
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
    self.logger.info("Config file:" + str(self._xapp._config_data))
    
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
        sleep(1) # Sleeps for 1 second
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

The xApp HTTP REST communication is identical to any other application.
The only requirement is specifying the `http` port in the config-file for the http service to be created during the xApp installation.

Although the HTTP REST communication can be freely implemented by the developer, OSC's RIC platform expects the xApp to implement clients and/or servers for the below scenarios:
- xApp registration and deregistration
- Config-file request
- Liveness and readiness probes

## xApp registration and deregistration

The Application Manager (AppMgr) is responsible for managing the xApp lifecycle.
It accounts for running xApps by maintaining a list of registered xApps.
For example, when the AppMgr registers or deregisters an xApp, it sends the list of all registered xApps to the Routing Manager (RtMgr), which distributes updated routes for all xApps and RIC components.
Updating this list is done by the xApp sending registration and deregistration requests during its startup and termination, respectively.
Both request are HTTP messages carrying a JSON with xApp data.
Also, both are already implemented in OSC's Python xApp framework `_BaseXapp` class, so xApps written using either `Xapp` or `RMRXapp` classes do not need to re-implement them.

The registration request is an HTTP POST send by the xApp to the AppMgr during the `_BaseXapp` initilization (called during `Xapp` and `RMRXapp` initializations).
The message is sent to the AppMgr `http` service at port `8080` and path `/ric/v1/register`.
So, as the AppMgr is deployed at the `ricplt` namespace, the full URL is: `http://service-ricplt-appmgr-http.ricplt:8080/ric/v1/register`.
The framework constructs the JSON message as an object with the fields below:
- `"appName"`: `HOSTNAME` environmental variable, usually set as the config-file `name` value
- `"appInstanceName"`: `name` value from xApp's config-file
- `"appVersion"`: `version` value from xApp's config-file
- `"configPath"`: should be the HTTP path for requesting the xApp config-file JSON, but it is always set as empty (`""`), so the AppMgr uses the standard path `ric/v1/config`
- `"httpEndpoint"`: the `http` service endpoint, formatted as `<HTTP_SERVICE_IP>:<HTTP_SERVICE_PORT>`
- `"rmrEndpoint"`: the `rmrdata` (not `rmrroute`) service endpoint, formatted as `<RMR_SERVICE_IP>:<RMR_DATA_SERVICE_PORT>`
- `"config"`: the **dumped** config file JSON, which will be **serialized again** after dumping the registration request JSON

If the `config` field is not filled in, the AppMgr sends a config-file request (described in the next subsection) at the `configPath`. 

The deregistration request is an HTTP POST send by the xApp to the AppMgr during the xApp termination when the `stop` method from `_BaseXapp` class is called.
The message is sent to the AppMgr `http` service at port `8080` and path `/ric/v1/deregister`.
So, as the AppMgr is deployed at the `ricplt` namespace, the full URL is: `http://service-ricplt-appmgr-http.ricplt:8080/ric/v1/deregister`.
The framework constructs the JSON message as an object with the fields below:
- `"appName"`: `HOSTNAME` environmental variable, usually set as the config-file `name` value
- `"appInstanceName"`: `name` value from xApp's config-file

Both registration and deregistration requests have a response send by the AppMgr to the xApp `http` service endpoint with path `/ric/v1/` 

## Config-file request

## Liveness and readiness probes

Liveness and readiness probes should be configured in the config-file at the same level of `name`, `version`, `containers`, and `messaging`.
The JSON object in the config-file must define, for both probes:
- `"httpGet"`: an object with `"path"` and `"port"` containing strings for the HTTP path and port 
- `"initialDelaySeconds"`: a string with the number of seconds that should be waited after the xApp installation to send the first liveness probe
- `"periodSeconds"`: a string with the number of seconds that should be waited to resend the liveness probe

Below we have examples for the config-file JSON object defining liveness and readiness probes:

```json
"livenessProbe": {
    "httpGet": {
        "path": "ric/v1/health/alive",
        "port": "8080"
    },
    "initialDelaySeconds": "5",
    "periodSeconds": "15"
}
```

```json
"readinessProbe": {
    "httpGet": {
        "path": "ric/v1/health/alive",
        "port": "8080"
    },
    "initialDelaySeconds": "5",
    "periodSeconds": "15"
}
```

------------------------------------------------------------------------ **EXERCISE X** ------------------------------------------------------------------------

Send HTTP requests to interesting RIC components paths 

------------------------------------------------------------------------ **EXERCISE X** ------------------------------------------------------------------------

Set an HTTP server to respond healthcheck and config requests

**Next steps**

create an xApp 3 as RMRXapp to be referred as an RMRXapp example in this class