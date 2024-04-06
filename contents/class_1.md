# Class 1: Managing the xApps 
At the end of this class, you should be able to:
- Onboard, install, and uninstall xApps
- Check xApp pods, services, and logs
- Check registered xApps in the Application Manager
- Manage the main aspects of an xApp descriptor (config-file)
- Manage the main aspects of a static xApp route table

All exercises in this class refer to the `xapp-1-deploy-test` xApp, located in `xapp-workshop/exercise-xapps/xapp-1-deploy-test` folder. It is highly advisable to change to the xApp directory as every command assumes that it is the actual directory.

# Managing the xApp lifecycle

In OSC's Near-RT RIC Kubernetes cluster, every xApp is installed as a pod, which contains one or more Docker containers, and a set of services, which addresses the pod's open ports. The information necessary to construct the xApp's pod and services is written in the xApp descriptor, commonly known as **config-file**. An optional **schema** file may accompany the config-file to validate its control section syntax. Both are `.json` files that can be found inside the `init/` directory.

OSC provides a command line tool that facilitates the xApp management, the **dms_cli**.

## Onboarding

For the xApp to be instantiated by the Application Manager (AppMgr) in the Near-RT RIC platform, the first step is to **onboard** the xApp. This process consists of generating a Helm chart that describes the xApp and is available at a **Helm chart repository** (chartmuseum). To be accessed, the chartmuseum URL must be set in the `CHART_REPO_URL` environmental variable (already set on the blueprint).

Given the **config-file** and **schema** JSONs, the **dms_cli** can onboard the xApp, which verifies if there is any error in the xApp configuration, then generating the xApp **Helm chart** and pushing it to the charmuseum. 

**EXERCISE 1**

Onboard the `xapp-1-deploy-test` xApp.

```bash
dms_cli onboard <CONFIG_FILE_PATH> <SCHEMA_PATH>
```

<p>
<details>
<summary>Solution</summary>

```bash
dms_cli onboard init/config-file.json init/schema-file.json
```

</details>
</p>

**EXERCISE 2**

Check onboarded xApps.

```bash
dms_cli get_charts_list
```

## Installing

Onboarded xApps can be installed by triggering the AppMgr to read the xApp Helm chart and instantiate the xApp pod and services in a Kubernetes namespace. By standard, the namespace for installing OSC xApps is `ricxapp`.

The identification for an xApp Helm chart is a **name** and a **version**, both obrigatorily described in the xApp's config-file.

**EXERCISE 3**

Install the onboarded `xapp-1-deploy-test` xApp.

```bash
dms_cli install <XAPP_NAME> <XAPP_VERSION> <NAMESPACE>
```

<p>
<details>
<summary>Solution</summary>

```bash
dms_cli install xapp-1-deploy-test 1.0.0 ricxapp
```

</details>
</p>


## Uninstalling

In OSC's Near-RT RIC there can not be two xApps with the same name in the same namespace. From that, the identifier for the running xApp instance consists of only its **name** and **namespace**.

Note that two versions of the same xApp can not be running simultaneously, although both can be onboarded. That is why the installation requires the xApp version!

The dms_cli also has `upgrade` and `rollback` commands to deal with xApp versions, but as both are equal to uninstalling the running version and installing another one, they can be ignored.

**EXERCISE 4**

Uninstall the `xapp-1-deploy-test`.

```bash
dms_cli uninstall <XAPP_NAME> <NAMESPACE>
```

<p>
<details>
<summary>Solution</summary>

```bash
dms_cli uninstall xapp-1-deploy-test ricxapp
```

</details>
</p>

## Checking the xApp

Pods

```bash
kubectl -n <NAMESPACE> get pods 
```

Logging

```bash
kubectl -n <NAMESPACE> logs POD/<XAPP_POD_NAME> 
```

Registered xApps

```bash
curl -X GET http://$(kubectl get pods -n ricplt -o wide | grep appmgr | awk '{print $6}'):8080/ric/v1/xapps
```

Services

```bash
kubectl -n <NAMESPACE> get svc
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

