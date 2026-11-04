# Automated devstack installation

This repo holds an automated devstack installation setup. It has been tested on Linux only. Software dependencies for successful setup are [Vagrant](https://learn.hashicorp.com/tutorials/vagrant/getting-started-install?in=vagrant/getting-started), [Virtualbox](https://www.vagrantup.com/docs/providers/virtualbox) and [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html). Please install them before trying this out.

It takes approximately 30 minutes to have a devstack environment up and running.

## Minimum requirements
### Hardware requirements
At least 16GB of RAM - Devstack is assigned 6GB of RAM   
At least 100GB of free disk space - Devstack is assigned default 40GB of disk space  
At least 8 virtual cores - Devstack is assigned 3 cores.

### Software requirements
Linux Operating system  
Working Ansible instance  
Working Vagrant instance  
Working Virtualbox instance(Used as the vagrant provider)
### Internet 
Fast internet connection. Advised to have at least 20MBps since devstack installs a lot of packages from the internet.


## Usage
Git clone this repo and within the cloned directory run the command
```bash
vagrant up
```
Wait for 30 minutes for the set up to finish and enjoy your new devstack set up.

## Check DevStack service status

After provisioning completes, run the local status command inside the VM:

```bash
vagrant ssh -c devstack-status
```

The command checks the systemd state of each service listed in
`assistant/expected_services.json`, prints recent journal output and cautious
next-step guidance for services that are not active, and exits with status `1`
if any configured service is not confirmed running. It is installed before
`stack.sh` runs, so it is available for troubleshooting an unsuccessful setup.
To get machine-readable output, use:

```bash
vagrant ssh -c 'devstack-status --json'
```

For more log context, inspect a reported unit directly, for example:

```bash
vagrant ssh -c 'sudo journalctl -u devstack@n-cpu.service -n 100 --no-pager'
```

The inventory covers baseline core services and Manila services configured by
this repository. Update it if you change enabled services in `local.conf.j2`.
A service reported as `NOT FOUND` may have a different unit name or may not be
enabled in the installed DevStack version. `RUNNING` means systemd reports the
unit active; it does not by itself verify that the service API is responding.
The suggested next steps are local rules based on unit state and common log
messages; inspect the journal before applying any suggested restart.

## Connect an MCP chat host

The MCP server runs on the host machine, from this repository, because it
controls the Vagrant VM. It exposes status, start, destroy, and operation
progress tools. Start and destroy run asynchronously; use the returned
`operation_id` with `get_devstack_operation_status` to check progress.

Create a separate Python environment and install the MCP SDK:

```bash
python3 -m venv .venv-mcp
.venv-mcp/bin/pip install -r assistant/requirements.txt
```

Configure an MCP-compatible chat host to launch
`.venv-mcp/bin/python /absolute/path/to/devstack-setup/assistant/mcp_server.py`
as a **stdio** MCP server. MCP host configuration formats differ; use that
command and argument in the host's local server configuration. A sample
`mcpServers` entry is in `assistant/mcp_config.example.json`; replace both
paths with absolute paths and adapt the wrapper shape to your host if needed.
Keep the host and server local to the trusted machine because the server can
start and inspect this repository's VM.

Destroy support is disabled by default. To expose the destroy tool, set
`DEVSTACK_MCP_ENABLE_DESTROY=1` in the MCP server's environment. Calling the
tool then asks the connected host for direct user confirmation before
destroying `devstack-vm` and its virtual disk. A host that cannot perform MCP
user elicitation cannot destroy the VM. The tool never accepts a VM name or
shell command from the model.
