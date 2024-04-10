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

## Building



## Pushing

## Installing

Onboarded xApps can be installed by triggering the AppMgr to read the xApp Helm chart and instantiate the xApp pod and services in a Kubernetes namespace. By standard, the namespace for installing OSC xApps is `ricxapp`.

The identification for an xApp Helm chart is a **name** and a **version**, both obrigatorily described in the xApp's config-file.

**EXERCISE X**

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

In OSC's Near-RT RIC there can not be two xApps with the same name in the same namespace. Because of that, the identifier of a running xApp instance consists of only its **name** and **namespace**.

Note that two versions of the same xApp can not be running simultaneously, although both can be onboarded and available on the chartmuseum. That is why the installation requires the xApp version!

The dms_cli also has `upgrade` and `rollback` commands to deal with xApp versions, but as both are equal to uninstalling the running version and installing another one, they can be ignored.

**EXERCISE X**

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

# Checking the xApp

This section explores how to check basic xApp informations. Make sure of having a running xApp in your deployment. If you uninstalled it in the previous exercise, install it again. 

## Pods

As xApps and OSC's Near-RT RIC components are deployed as Kubernetes pods, we can use Kubernetes' `kubectl get pods` command to check running pods and their status. It requires a namespace to look for pods, which is informed using the `-n` option. Alternatively, the `-A` option can be used to list pods from all namespaces, instead of only one.

Other important option is `-o wide`, which expands the information outputted for the pods. This might be needed to get their IPs.

The namespace for components of the Near-RT RIC platform is `ricplt`, while the standard namespace for xApps is `ricxapp`. 

**EXERCISE X**

Check the name and IP of the pods of all running xApps.
```bash
kubectl -n <NAMESPACE> get pods -o wide
```

<p>
<details>
<summary>Solution</summary>

```bash
kubectl -n ricxapp get pods -o wide
```

</details>
</p>

## Logging

The logs of OSC's Near-RT RIC components and xApps using OSC's xApp frameworks can be printed by using the `kubectl logs` command. It requires the pod's name (accessable using the `kubectl get pods` command) and namespace.

**EXERCISE X**

```bash
kubectl -n <NAMESPACE> logs POD/<XAPP_POD_NAME> 
```

<p>
<details>
<summary>Solution</summary>

This is a generic solution to look for the pod's name and use it for logging.

```bash
kubectl -n ricxapp logs POD/$(kubectl get pods -n ricxapp | grep xapp1deploytest | awk '{print $1}')> 
```

</details>
</p>

## Registered xApps

When an xApp starts to run, one of its first tasks is to register to the AppMgr. As much problems may occur if the xApp is not registered (e.g. the route between an E2 Node and an xApp may not be created), it is important to consult the AppMgr for registered xApps.

The AppMgr exposes the `8080` port for HTTP communication. To obtain the AppMgr's list of registered xApps in a JSON, send an HTTP GET request to the path `/ric/v1/xapps`.

**EXERCISE X**

Consult the AppMgr to get the registered xApps. Remember you can use `kubectl -n ricplt get pods -o wide` to get the AppMgr's IP. 

```bash
curl -X GET http://<APPMGR_IP>:8080/ric/v1/xapps
```

<p>
<details>
<summary>Solution</summary>

This is a generic solution that looks for the AppMgr's IP and sends the HTTP GET request to it.

```bash
curl -X GET http://$(kubectl get pods -n ricplt -o wide | grep appmgr | awk '{print $6}'):8080/ric/v1/xapps
```

</details>
</p>

## Services

Kubernetes pods expose their ports as Kubernetes services, which have their own IP and hostname. Services from OSC's Near-RT RIC components and xApps have their hostnames standardized as `service-<NAMESPACE>-<NAME>-<PORT_TYPE>`, where the port type might be `http` or `rmr`. Service hostnames are commonly used when writing static routing tables or referring to endpoints inside xApp source codes.

Checking for services can be done using the `kubectl get svc` command, which works similar to `kubectl get pods`. The namespace should be informed with `-n`, otherwise, `-A` can be used to list services from all namespaces. Extra information can also be obtained with the `-o wide` option.

**EXERCISE X**

Check for available services for all running xApps.

```bash
kubectl -n <NAMESPACE> get svc -o wide
```

<p>
<details>
<summary>Solution</summary>

```bash
kubectl -n ricxapp get svc -o wide
```

</details>
</p>

# Config-file (xApp descriptor)

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


**EXERCISE X**

Edit the `config-file.json` to change the xApp's name and version. The version must be three numbers separated by a `.`, otherwise the config-file won't pass dms_cli validation.  Onboard the xApp again and check if anything changed in the xApp charts list (using the `dms_cli`).

<p>
<details>
<summary>Solution</summary>

Config-file after an arbitrary modification in the xApp's name and version.

```json
{
    "name": "anotherxappname",
    "version": "2.3.4",
...

```

Onboarding the xApp and checking the chart list:

```bash
dms_cli onboard init/config-file.json init/schema-file.json
dms_cli get_charts_list
```

</details>
</p>

**EXERCISE X**

Re-install the xApp with the new configuration and check if there is any changes in the xApp pod and services.

<p>
<details>
<summary>Solution</summary>

Uninstalling the previous xApp (`xapp1deploytest`) and installing the new one (assuming that its name is `anotherxappname` and its version is `2.3.4`):

```bash
dms_cli uninstall xapp1deploytest ricxapp
dms_cli install anotherxappname 2.3.4 ricxapp
```

Checking for its pod and services:

```bash
kubectl -n ricxapp get pods
kubectl -n ricxapp get svc
```

</details>
</p>

## Messaging

Besides `"name"`, `"version"`, and `"containers"`, the `"messaging"` section is the last obrigatory one. With these four section defined, a config-file can pass the dms_cli checks and be used by the AppMgr to instantiate an xApp.    

For the xApp to be installed, it is required to specify at least one RMR port. In our example, only the RMR data port (for RMR messages) is open, at port 4560. 

**EXERCISE X**

Check the available open ports of the xApp.

<p>
<details>
<summary>Solution</summary>

```bash
kubectl -n ricxapp get svc
```

There is only one service, which refers to the RMR data port (4560).

</details>
</p>

**EXERCISE X**

Edit the `config-file.json` as described below:
- Add a port with name "http" at port 8080
- Add a port with name "rmrroute" at port 4561
- Add a random port (choose any name and port)

Onboard this new config-file and re-install the xApp (uninstall the xApp and then install it again). Check the available open ports of the xApp again. What has changed?

<p>
<details>
<summary>Solution</summary>

Assuming the xApp container is named `xapp1deploytestcontainer` in the descriptor, this should be the config-file after the modifications:

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

Checking the xApp services:

```bash
kubectl -n ricxapp get svc
```

There should be three services:
- RMR: its hostname ends with `-rmr` and has 4560 (RMN data) and 4561 (RMR route) ports open
- HTTP: its hostname ends with `-http` and has 8080 port open
- MyPort: its hostname ends with `-myport` and has 12345 port open

</details>
</p>

### RMR data port

The `rmrdata` port can have some special additional fields in the config-file:
- `"txMessages"`: contains an array of strings, each one being a type of message that the xApp may transmit via RMR
- `"rxMessages"`: contains an array of strings, each one being a type of message that the xApp may receive via RMR
- `"policies"`: contains an array of integers, each one being a policy that the xApp can receive via the A1 interface

**EXERCISE X**

Add the fields described above to the `rmrdata` port in the config-file to specify the messages and policies below:
- Transmitted message types: `RIC_SUB_REQ` and `RIC_SUB_DEL_REQ`
- Received message types: `RIC_SUB_RESP`, `RIC_INDICATION`, and `RIC_SUB_DEL_RESP`
- A1 policies: `1`

<p>
<details>
<summary>Solution</summary>

Assuming the xApp container is named `xapp1deploytestcontainer` in the descriptor, this should be the config-file after the modifications:

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

