Unit tests
==========

Some of these tests are dependent on environment variables, AppArmor, sudoers, another system account, and additional virtualenvs. You may prefer to just rely on the GitHub Actions CI on your PR rather than setting up your local machine correctly.

There are not yet directions for local setup, but here are some breadcrumbs to follow:

- ``.github/workflows/ci.yml`` installs an AppArmor profile (this has to be done outside of any Docker container), builds a Dockerimage (see ``Dockerfile``), and runs tests via Makefile commands.
- The Make targets set environment variables for testing proxy vs. non-proxy setups, but otherwise run pytest directly.
- Codejail "magically" detects the presence of a sandbox virtualenv based on directory naming and auto-configures itself, but can fall back to environment variables ``CODEJAIL_TEST_USER`` and ``CODEJAIL_TEST_VENV``. See code around ``running_in_virtualenv`` in ``codejail/jail_code.py``.
