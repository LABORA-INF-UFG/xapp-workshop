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

# Logging with `mdclogpy`

# Interacting with the SDL

Explain what is an SDL namespace

SDL funtions implemented in the `_BaseXapp` class:
- `sdl_set`: 
- `sdl_get`:
- `sdl_find_and_get`:
- `sdl_delete`:

# Implementing HTTP REST communication