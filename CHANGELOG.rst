Changelog
#########

..
   All enhancements and patches to codejail will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

*

4.0.0 - 2025-06-13
******************

Changed
=======

* **BREAKING**: Require an explicit opt in to unsafety; defer decision to call
  time rather than module load time.

  * Calling ``safe_exec`` without having configured the codejail library will
    now raise an exception rather than passing execution to ``not_safe_exec``.
    (Note: This does not prevent other kinds of dangerous misconfiguration, such
    as a bad or missing AppArmor profile.)
  * In installations that are intended to always run in safe mode, and have been
    properly configured to do so, this should have no effect.
  * In installations where codejail sometimes needs to run with no sandboxing
    (e.g. in unit tests), developers will need to set
    ``codejail.safe_exec.ALWAYS_BE_UNSAFE`` to ``True``. This can be set from a
    unit test harness, for example.

Added
=====

* Support for Django 5.2
