# Class 1: Managing the xApps 

## Managing the xApp lifecycle

Onboarding

```bash
dms_cli onboard <CONFIG_FILE_PATH> <SCHEMA_PATH>
```

Installing

```bash
dms_cli install <XAPP_NAME> <XAPP_VERSION> <NAMESPACE>
```

Uninstalling

```bash
dms_cli uninstall <XAPP_NAME> <NAMESPACE>
```

## Checking the xApp

Pods

```bash
kubectl get pods -n <NAMESPACE>
```

Logging

```bash
kubectl logs POD/<XAPP_POD_NAME> -n <NAMESPACE>
```

Services

```bash
kubectl get svc -n <NAMESPACE>
```

## Config-file (xApp descriptor)

The obrigatory fields defined by the xApp descriptor in the config-file are:
- `"name"`: the xApp name
- `"version"`: the xApp version
- `"containers"`: the list of containers of the xApp pod

Each element in the `containers` array must have at least:
- `"name"`: the name of the container used for reference in the config-file
- `"image"`: the Docker image address for that container

The `"image"` is defined by 3 fields:
- `"registry"`: the address to the Docker registry hosting the image, including its port
- `"name"`: the image name
- `"tag"`: the image tag (its version)



Edit the `config-file.json` as described below:
- Change the xApp name and version
- Change the xApp image name and tag

Re-install the xApp with the new configuration.

### Messaging

Besides the xApp name, version and 

For the xApp to be installed, it is required to specify at least one RMR port. In our example, only the RMR data port (for RMR messages) is open, at port 4560. 

Check the xApp services and pay atention to the open ports.

Edit the `config-file.json` as described below:
- Add a port with name "http" at port 8080
- Add a port with name "rmrroute" at port 4561
- Add a random port (choose any name and port)

<p>
<details>
<summary>Solution</summary>

Assuming the xApp container is named `xapp1deploytestcontainer` in the descriptor.

```json
...
"ports":[
    {
        "name": "rmrdata",
        "container": "xapp1deploytestcontainer",
        "port": 4560,
        "description": "rmr data port for rmr messages from RIC components"
    },
    {
        "name": "rmrroute",
        "container": "xapp1deploytestcontainer",
        "port": 4560,
        "description": "rmr route port for routes from RtMgr"
    },
    {
        "name": "http",
        "container": "xapp1deploytestcontainer",
        "port": 8080,
        "description": "http port"
    },
    {
        "name": "myport",
        "container":"xapp1deploytestcontainer",
        "port": 12345,
        "description": "a port"
    }
]

```
</details>
</p>

Re-install the xApp and check its services again. Is there any change?

<p>
<details>
<summary>Solution</summary>

The `service-ricxapp-xapp1deploytest-rmr` service has a new `4561/TCP` port. There is also a new `service-ricxapp-xapp1deploytest-http` service with an open `8080/TCP` port and another `service-ricxapp-xapp1deploytest-myport` at port `12345/TCP`.

</details>
</p>

The `rmrdata` port can have some special additional fields in the config-file:
- `"txMessages"`: contains an array of strings, each one being a type of message that the xApp may transmit via RMR
- `"rxMessages"`: contains an array of strings, each one being a type of message that the xApp may receive via RMR
- `"policies"`: contains an array of integers, each one being a policy that the xApp can receive via the A1 interface

Add the fields above to the `rmrdata` port to specify the messages and policies below:
- Transmitted message types: `RIC_SUB_REQ` and `RIC_SUB_DEL_REQ`
- Received message types: `RIC_SUB_RESP`, `RIC_INDICATION`, and `RIC_SUB_DEL_RESP`
- A1 policies: `1`

<p>
<details>
<summary>Solution</summary>

```json
{
    "name": "rmrdata",
    "container": "xapp1deploytestcontainer",
    "port": 4560,
    "rxMessages": ["RIC_SUB_RESP", "RIC_INDICATION","RIC_SUB_DEL_RESP"],
    "txMessages": ["RIC_SUB_REQ","RIC_SUB_DEL_REQ"],
    "policies": [1],
    "description": "rmr data port"
}
```

</details>
</p>

## Route file

