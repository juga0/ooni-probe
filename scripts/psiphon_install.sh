#!/bin/sh

#FIXME remove x
set -ex

PSIPHON_PATH=$HOME/test
PSIPHON_PYCLIENT_PATH=$PSIPHON_PATH/psiphon-circumvention-system/pyclient

mkdir -p $PSIPHON_PATH

command_exists() {
	command -v "$@" > /dev/null 2>&1
}

user="$(id -un 2>/dev/null || true)"

sh_c='sh -c'

if [ "$user" != 'root' ]; then
	if command_exists sudo; then
		sh_c='sudo sh -c -E'
	elif command_exists su; then
		sh_c='su -c --preserve-environment'
	else
		echo >&2 'Error: this installer needs the ability to run commands as root.'
		echo >&2 'We are unable to find either "sudo" or "su" available to make this happen.'
		exit 1
	fi
fi

echo "installing dependencies"
$sh_c "apt-get -y install zlib1g-dev libssl-dev"

if [ -z "command_exists hg" ]; then
    $sh_c "apt-get -y install mercurial"
fi

echo "cloning psiphon repository"
cd $PSIPHON_PATH
hg clone https://bitbucket.org/psiphon/psiphon-circumvention-system
echo "psiphon repository cloned"

# optional, compile their ssh
echo "compiling psiphon ssh"
cd psiphon-circumvention-system/Server/3rdParty/openssh-5.9p1/
./configure
make
mv ssh ../../../pyclient/
make clean
echo "psiphon ssh compiled"

# check if we are in a virtualenv, create it otherwise
echo "checking virtualenv"
if [ python -c 'import sys; print hasattr(sys, "real_prefix")'  = "False"];then
    # we are not in a virtualenv
    # create a virtualenv
    # FIXME: assuming debian version will have secure pip/virtualenv
    if [ -z "command_exists virtualenv" ]; then
        $sh_c "apt-get -y install python-virtualenv"
    fi
    if [ ! -f $HOME/.virtualenvs/ooniprobe/bin/activate ]; then
      # Set up the virtual environment
      mkdir -p $HOME/.virtualenvs
      virtualenv $HOME/.virtualenvs/ooniprobe
      source $HOME/.virtualenvs/ooniprobe/bin/activate
    else
      source $HOME/.virtualenvs/ooniprobe/bin/activate
    fi
fi
echo "virtualenv activated"

# create psi_client.dat
echo "creating servers data file"
echo "installing dependencies to create servers data file"
pip install -v --timeout 60  wget
cd /tmp
cat <<EOF > psi_generate_dat.py
#!/usr/bin/env python

import wget
import os
import json

# Delete 'server_list' if exists
if os.path.exists("server_list"):
    # os.remove("server_list")
    # os.rename("server_list", "server_list")
    pass
else:
    # Download 'server_list'
    url ="https://psiphon3.com/server_list"
    wget.download(url)

# convert server_list to psi_client.dat
dat = {}
dat["propagation_channel_id"] = "FFFFFFFFFFFFFFFF"
dat["sponsor_id"] = "FFFFFFFFFFFFFFFF"
dat["servers"] = json.load(open('server_list'))['data'].split()
json.dump(dat, open('psi_client.dat', 'w'))
EOF

chmod +x psi_generate_dat.py
./psi_generate_dat.py
echo "servers data file created"
chmod +x psi_generate_dat.py
./psi_generate_dat.py
echo "servers data file created"
mv psi_client.dat $PSIPHON_PYCLIENT_PATH


echo "[+] Installing all of the Python dependency requirements with pip in your virtualenv!";
pip install -v --timeout 60  jsonpickle pexpect

# run psiphon
# cd $PSIPHON_PYCLIENT_PATH
# python psi_client.py