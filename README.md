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
