Vagrant.configure("2") do |config|
    config.vm.define "devstack-vm-blog"
    config.vm.box = "ubuntu/focal64"
    #config.vm.network "private_network", ip: "10.123.123.123", nic_type: "virtio"
    config.vm.network "private_network", type: "dhcp", nic_type: "virtio"

    config.vm.provider "virtualbox" do |v|
        v.name = "devstack-vm-blog"
        v.memory = 6144
        v.cpus = 3
        v.customize ["modifyvm", :id, "--nested-hw-virt", "on"]
        v.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
    end

    config.vm.provision "ansible" do |ansible|
        ansible.verbose = "v"
        ansible.playbook = "devstack-setup.yml"
    end
end