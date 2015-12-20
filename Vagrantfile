# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/trusty64"

  # config.vm.network "private_network", ip: "192.168.33.240"

  config.vm.synced_folder ".", "/home/vagrant/codejail"
    #, type: "nfs",
    # mount_options: ['rw', 'vers=3', 'tcp', 'fsc' ,'actimeo=2']

  config.vm.provision "shell", path: "vagrant/provision.sh"
end
