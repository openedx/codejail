Change Log
##########

..
   All enhancements and patches to {{ cookiecutter.sub_dir_name }} will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

*

4.0.0 – 2023-11-31
******************

Added
=====

* Django setting ``CODE_JAIL['always_unsafe']`` changes all ``safe_exec`` calls into ``not_safe_exec`` calls, bypassing sandboxing. This is required for use in devstack or other containerized development environments.

Changed
=======

* **Breaking change:** When codejail is not configured for Python, reject execution rather than allowing execution to proceed without any sandboxing.

  * This change should not cause a problem for any properly configured server. If it causes failures, this likely means that the server was running user code without any protections, and a security investigation is warranted.
  * In containerized development environments, this change will cause codejail executions to start failing unless ``CODE_JAIL['always_unsafe']`` is set. (Codejail cannot sandbox code inside a Docker container.)
