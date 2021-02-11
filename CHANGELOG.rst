Changelog
#########

.. All enhancements and patches to will be documented in this file.  It adheres to the structure of https://keepachangelog.com/, but in reStructuredText instead of Markdown (for ease of incorporation into Sphinx documentation and the PyPI description). This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

[Unreleased]
============

Changed
-------

- **Breaking change**: ``safe_exec`` and ``not_safe_exec`` no longer modify the ``globals_dict`` parameter, and instead return a new dictionary containing the state of the globals at the end of the execution. If you wish to preserve the old behavior, you can change a call like ``safe_exec(code, globals_dict)`` to ``globals_dict.update(safe_exec(code, globals_dict))``.
- Accordingly, ``globals_dict`` is now an optional (keyword) parameter, defaulting to ``{}``.

[3.1.3] - 2020-11-09
====================
No changelog notes before this point; see notes on `GitHub releases <https://github.com/edx/codejail/releases>`_.
