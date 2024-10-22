ARG ubuntu_version="20.04"

FROM ubuntu:${ubuntu_version}
SHELL ["/bin/bash", "-c"]

ARG python_version="3.8"

# Install Codejail Packages
ENV TZ=Etc/UTC
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && apt-get upgrade -y
RUN apt-get install -y vim python${python_version} python${python_version}-dev python${python_version}-distutils
RUN apt-get install -y sudo git make curl build-essential
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python${python_version}
RUN pip install virtualenv

# Define Environment Variables
ENV CODEJAIL_GROUP=sandbox
ENV CODEJAIL_SANDBOX_CALLER=ubuntu
ENV CODEJAIL_TEST_USER=sandbox
ENV CODEJAIL_TEST_VENV=/home/sandbox/codejail_sandbox-python${python_version}

# Create Virtualenv for sandbox user
RUN virtualenv -p python${python_version} --always-copy $CODEJAIL_TEST_VENV

RUN virtualenv -p python${python_version} venv
ENV VIRTUAL_ENV=/venv

# Add venv/bin to path
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create Sandbox user & group
RUN addgroup $CODEJAIL_GROUP
RUN adduser --disabled-login --disabled-password $CODEJAIL_TEST_USER --ingroup $CODEJAIL_GROUP

# Switch to non root user inside Docker container
RUN getent group ubuntu || groupadd ubuntu
RUN getent passwd ubuntu || adduser --disabled-login --disabled-password ubuntu --ingroup ubuntu

# Remove using PAM to set limits for sudo.
# We want codejail to manage the limits so we remove this line from the sudo pam config
# if we don't the forked process gets limits based on /etc/security/limits.conf which by
# default does not set any limits on the forked process.
# This line was not there on Ubuntu 20.04 but was added in 22.04
RUN sed -i '/pam_limits.so/d' /etc/pam.d/sudo

# Give Ownership of sandbox env to sandbox group and user
RUN chown -R $CODEJAIL_TEST_USER:$CODEJAIL_GROUP $CODEJAIL_TEST_VENV

WORKDIR /codejail

# Clone Requirement files
COPY ./requirements/sandbox.txt /codejail/requirements/sandbox.txt
COPY ./requirements/testing.txt /codejail/requirements/testing.txt

# Install codejail_sandbox sandbox dependencies
RUN source $CODEJAIL_TEST_VENV/bin/activate && pip install -r /codejail/requirements/sandbox.txt && deactivate

# Install testing requirements in parent venv
RUN pip install -r /codejail/requirements/sandbox.txt && pip install -r /codejail/requirements/testing.txt

# Clone Codejail Repo
COPY . /codejail

# Setup sudoers file
COPY sudoers-file/01-sandbox-python-${python_version} /etc/sudoers.d/01-sandbox

# Change Sudoers file permissions
RUN chmod 0440 /etc/sudoers.d/01-sandbox

# Change Repo ownership
RUN chown -R ubuntu:ubuntu ../codejail

# Switch to ubuntu user
USER ubuntu
