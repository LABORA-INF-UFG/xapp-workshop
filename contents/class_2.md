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

OSC provides a logging library called `mdclogpy`.
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
- `"mdc"`: an object containing all existing key-value pairs of Mapped Diagnostic Context (MDC), e.g. the pod and service name
- `"msg"`: the message logged

Although the `mdclogpy` has functions to fully customize the MDC, it also provides a `get_env_params_values` method to generate an MDC with the process ID and the values of the environmental variables `SYSTEM_NAME`, `HOST_NAME`, `SERVICE_NAME`, `CONTAINER_NAME`, and `POD_NAME`.

The code below exemplifies the main aspects of the `mdclogpy` logger:  

```python
from mdclogpy import Logger, Level
logger = Logger(name="xapp_name", level=Level.WARNING)
logger.get_env_params_values()
logger.error("This is a log at the ERROR level")
logger.warning("This is a log at the WARNING level")
logger.info("This is a log at the INFO level")
logger.debug("This is a log at the DEBUG level")
```

Executing the code above without setting the environmental variables consulted by `get_env_params_values` will generate logs similar to:

```json
{"ts": 1714634514940, "crit": "ERROR", "id": "xapp_name", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 3145453}, "msg": "This is a log at the ERROR level"}
{"ts": 1714634546562, "crit": "WARNING", "id": "xapp_name", "mdc": {"SYSTEM_NAME": "", "HOST_NAME": "", "SERVICE_NAME": "", "CONTAINER_NAME": "", "POD_NAME": "", "PID": 3145453}, "msg": "This is a log at the WARNING level"}
```

# Interacting with the SDL

Explain what is an SDL namespace

SDL funtions implemented in the `_BaseXapp` class:
- `sdl_set`: 
- `sdl_get`:
- `sdl_find_and_get`:
- `sdl_delete`:

# Implementing HTTP REST communication