#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR/..


sudo apt-get update
sudo apt-get install -y virtualenvwrapper
sudo apt-get install -y python-dev python-numpy python-scipy

sudo bash -e <<BASH
    cd /home/vagrant/
    virtualenv sandboxenv

    source sandboxenv/bin/activate

    cd codejail

    pip install -r vagrant/requirements/fake-sandbox.txt
BASH

sudo addgroup sandbox
sudo adduser --gecos --disabled-login sandbox --ingroup sandbox

sudo addgroup www-data
sudo adduser --gecos --disabled-login www-data --ingroup www-data

SANDBOX_FILE=`mktemp`

sudo tee $SANDBOX_FILE <<SUDOERS
    www-data ALL=(sandbox)  SETENV:NOPASSWD:/home/vagrant/sandboxenv/bin/python
    www-data ALL=(sandbox)  SETENV:NOPASSWD:/usr/bin/find /tmp/codejail-*/tmp -mindepth 1 -maxdepth 1 -exec rm -rf {} ;
    www-data ALL=(ALL) NOPASSWD:/bin/kill
    www-data ALL=(ALL) NOPASSWD:/usr/bin/pkill
SUDOERS

cat $SANDBOX_FILE | sudo EDITOR='tee -a' -- visudo -f /etc/sudoers.d/01-sandbox

rm $SANDBOX_FILE

sudo apt-get install -y apparmor apparmor-utils

sudo tee /etc/apparmor.d/home.vagrant.sandboxenv.bin.python <<ARMOR
#include <tunables/global>

/home/vagrant/sandboxenv/bin/python {
    #include <abstractions/base>

    /home/vagrant/sandboxenv/** mr,
    /home/vagrant/sandboxenv/lib/python2.7/** r,
    /tmp/codejail-*/ rix,
    /tmp/codejail-*/** wrix,

    #
    # Whitelist particiclar shared objects from the system
    # python installation
    #
    /usr/lib/python2.7/lib-dynload/_json.so mr,
    /usr/lib/python2.7/lib-dynload/_ctypes.so mr,
    /usr/lib/python2.7/lib-dynload/_heapq.so mr,
    /usr/lib/python2.7/lib-dynload/_io.so mr,
    /usr/lib/python2.7/lib-dynload/_csv.so mr,
    /usr/lib/python2.7/lib-dynload/datetime.so mr,
    /usr/lib/python2.7/lib-dynload/_elementtree.so mr,
    /usr/lib/python2.7/lib-dynload/pyexpat.so mr,

    #
    # Allow access to selections from /proc
    #
    /proc/*/mounts r,

}
ARMOR

sudo apparmor_parser /etc/apparmor.d/home.vagrant.sandboxenv.bin.python
# Use to disable `aa-complain /etc/apparmor.d/home.vagrant.sandboxenv.bin.python`
sudo aa-enforce /etc/apparmor.d/home.vagrant.sandboxenv.bin.python

make_jailenv_env() {
  cd ~
  virtualenv --system-site-packages jailenv
  source ~/jailenv/bin/activate

  cd codejail/

  python setup.py install
  pip install -r vagrant/requirements/codejail.txt
}

make_jailenv_env


sudo bash -e <<TEST
cd ~/codejail/
source ~/jailenv/bin/activate
nosetests vagrant/
TEST
