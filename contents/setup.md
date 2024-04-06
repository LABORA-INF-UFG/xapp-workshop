# Setup

All exercises in this workshop suppose that xApps are being built and deployed in a virtual machine (VM) running the [OpenRAN@Brasil Blueprint v1](https://github.com/LABORA-INF-UFG/openran-br-blueprint/wiki/OpenRAN@Brasil-Blueprint-v1). To deploy it, follow the instructions in the [Get started](https://github.com/LABORA-INF-UFG/openran-br-blueprint/wiki/OpenRAN@Brasil-Blueprint-v1#get-started) section to download the its image and install the VM.

Although the VM can be accessed directly via the VM manager chosen by the participant, it is highly advised to use an SSH connection via the [Visual Studio Code Remote Explorer](https://code.visualstudio.com/docs/remote/ssh) to maintain parity with the instructor's setup.

After accessing the VM terminal, download the workshop repository:
```bash
git clone https://github.com/LABORA-INF-UFG/xapp-workshop
```

# Code completion and referencing

To enable code completion and referencing in the context of the OSC Python xApp Framework, it is necessary to install some pip packages used in xApp development in the VM.

Do this by executing, in the VM terminal:

```bash
pip install ricxappframe mdclogpy
```