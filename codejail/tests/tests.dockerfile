FROM ubuntu:bionic

RUN apt-get update && apt-get install -y python python3.6 python3.7 python-virtualenv make sudo apparmor apparmor-utils
RUN useradd --create-home sandbox && echo "sandbox ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
COPY --chown=sandbox . /home/sandbox/codejail
WORKDIR /home/sandbox/codejail
USER sandbox
RUN virtualenv --python=python3 ../virtualenv-codejail && ../virtualenv-codejail/bin/pip install tox
ENV PATH=/home/sandbox/virtualenv-codejail/bin:$PATH
