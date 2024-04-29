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

## RMRXapp class

# Interacting with the SDL

Explain what is an SDL namespace

SDL funtions implemented in the `_BaseXapp` class:
- `sdl_set`: 
- `sdl_get`:
- `sdl_find_and_get`:
- `sdl_delete`:

# Implementing HTTP REST communication