FROM ubuntu:focal
SHELL ["/bin/bash", "-c"]

# Install Codejail Packages
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y vim python3-virtualenv python3-pip
RUN apt-get install -y sudo

# Define Environment Variables
ENV CODEJAIL_GROUP=sandbox
ENV CODEJAIL_SANDBOX_CALLER=ubuntu
ENV CODEJAIL_TEST_USER=sandbox
ENV CODEJAIL_TEST_VENV=/home/sandbox/codejail_sandbox-python3.8

# Create Virtualenv for sandbox user
RUN virtualenv -p python3.8 --always-copy $CODEJAIL_TEST_VENV

RUN virtualenv -p python3.8 venv
ENV VIRTUAL_ENV=/venv

# Add venv/bin to path
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create Sandbox user & group
RUN addgroup $CODEJAIL_GROUP
RUN adduser --disabled-login --disabled-password $CODEJAIL_TEST_USER --ingroup $CODEJAIL_GROUP

# Switch to non root user inside Docker container
RUN addgroup ubuntu
RUN adduser --disabled-login --disabled-password ubuntu --ingroup ubuntu

# Give Ownership of sandbox env to sandbox group and user
RUN chown -R $CODEJAIL_TEST_USER:$CODEJAIL_GROUP $CODEJAIL_TEST_VENV

# Clone Codejail Repo
ADD . ./codejail
WORKDIR /codejail

# Install codejail_sandbox sandbox dependencies
RUN source $CODEJAIL_TEST_VENV/bin/activate && pip install -r requirements/sandbox.txt && deactivate

# Install testing requirements in parent venv
RUN pip install -r requirements/sandbox.txt && pip install -r requirements/testing.txt

# Setup sudoers file
ADD sudoers-file/01-sandbox /etc/sudoers.d/01-sandbox

# Change Sudoers file permissions
RUN chmod 0440 /etc/sudoers.d/01-sandbox

# Change Repo ownership
RUN chown -R ubuntu:ubuntu ../codejail

# Switch to ubuntu user
USER ubuntu
