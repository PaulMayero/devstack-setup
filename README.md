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
