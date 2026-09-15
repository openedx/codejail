# Used for running codejail unit tests.
#
# Sandbox path and ABI version must be kept in sync with AppArmor profile.

ARG ubuntu_version="24.04"

FROM ubuntu:${ubuntu_version}
SHELL ["/bin/bash", "-c"]

ARG python_version="3.12"

# Install Codejail Packages
ENV TZ=Etc/UTC
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && apt-get upgrade -y
# ---------------------------------------------------------------------------
# - The "distutils" module was removed in Python 3.12 (PEP 632).
# - To ensure virtualenv creation still works, we use python3-venv instead.
# ---------------------------------------------------------------------------
RUN apt-get install -y vim python${python_version} python${python_version}-dev python${python_version}-venv || \
    apt-get install -y vim python${python_version} python${python_version}-dev python3-distutils
RUN apt-get install -y sudo git make curl build-essential
# ---------------------------------------------------------------------------
# - Ubuntu 24.04 enforces "externally-managed-environment" per PEP 668,
#   which prevents pip from modifying system packages by default.
# - We explicitly add "--break-system-packages" to allow pip installs inside
#   the container environment (since it's isolated anyway).
# ---------------------------------------------------------------------------
RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python${python_version} get-pip.py --break-system-packages && rm get-pip.py
RUN pip install virtualenv --break-system-packages

# Install uv for dependency management (install system-wide to /usr/local/bin)
# `pipefail` is required here: without it a failed curl is masked by the exit
# status of `sh`, so the layer succeeds without installing uv and the build only
# fails much later with "uv: command not found".
RUN set -o pipefail && \
    curl -LsSf --retry 5 --retry-all-errors https://astral.sh/uv/install.sh | \
    env UV_INSTALL_DIR=/usr/local/bin sh && \
    uv --version

# Define Environment Variables
ENV CODEJAIL_GROUP=sandbox
ENV CODEJAIL_SANDBOX_CALLER=ubuntu
ENV CODEJAIL_TEST_USER=sandbox
ENV CODEJAIL_TEST_VENV=/home/sandbox/codejail_sandbox

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

# Copy project files needed for dependency installation
COPY pyproject.toml uv.lock /codejail/

# Install sandbox dependencies into the sandbox virtualenv from the
# 'sandbox' dependency group
RUN uv pip install --python $CODEJAIL_TEST_VENV/bin/python --no-cache-dir --group sandbox

# Install CI dependencies (tox + tox-uv) into the main venv from the 'ci' group
RUN uv pip install --python $VIRTUAL_ENV/bin/python --no-cache-dir --group ci

# Clone Codejail Repo
COPY . /codejail

# Setup sudoers file
COPY sudoers-file/01-sandbox-python /etc/sudoers.d/01-sandbox

# Change Sudoers file permissions
RUN chmod 0440 /etc/sudoers.d/01-sandbox

# Change Repo ownership
RUN chown -R ubuntu:ubuntu ../codejail

# Switch to ubuntu user
USER ubuntu
