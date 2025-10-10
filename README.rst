CodeJail
========

CodeJail manages execution of untrusted code in secure sandboxes. It is
designed primarily for Python execution, but can be used for other languages as
well.

Security is enforced with AppArmor.  If your operating system doesn't support
AppArmor, or if the AppArmor profile is not defined and configured correctly,
then CodeJail will not protect the execution.

CodeJail is designed to be configurable, and will auto-configure itself for
Python execution if you install it properly.

A CodeJail sandbox consists of several pieces:

#) Sandbox environment. For a Python setup, this would be Python and
   associated core packages as a virtualenv. This is denoted throughout this document
   as **<SANDENV>**. This is read-only, and shared across sandbox instantiations.

   Sandboxed code also has access to OS libraries to the extent that the
   AppArmor profile permits it.

#) Sandbox execution directory. This is an ephemeral read-only directory named
   like ``/tmp/codejail-XXXXXXXX`` containing the submitted code
   (``./jailed_code``), optional additional files, and a writable temporary
   directory (``./tmp``) that the submitted code can use as a scratch space.

   The submitted code is typically the code submitted by the student to be
   tested on the server, and the additional files are typically a
   ``python_lib.zip`` containing grading or utility libraries.

To run, CodeJail requires two user accounts. One account is the main
account under which the code runs, which has access to create
sandboxes. This will be referred to as **<SANDBOX_CALLER>**. The
second account is the account under which the sandbox runs. This is
typically the account ``sandbox``.

Supported Versions
------------------

This library currently is tested to work with the following versions

Python:

* 3.11

Ubuntu:

* 22.04
* 24.04

(Note that the Python version used inside the sandbox may be different from the
version used for the library itself.)

Installation
------------

These instructions detail how to configure your operating system so that
CodeJail can execute Python code safely. However, it is also possible to set
``codejail.safe_exec.ALWAYS_BE_UNSAFE = True`` and execute submitted Python
directly on the machine, with no security whatsoever. This may be fine for
developers' machines who are unconcerned with security, and allows testing
an integration with CodeJail's API. It must not be used if any input is coming
from untrusted sources, however. **Do not use this option in production systems.**

To secure Python execution, you'll be creating a new virtualenv.  This means
you'll have two: the main virtualenv for your project, and the new one for
sandboxed Python code.

Choose a place for the new virtualenv, call it **<SANDENV>**.  It will be
automatically detected and used if you put it right alongside your existing
virtualenv, but with ``-sandbox`` appended.  So if your existing virtualenv is in
``/home/chris/ve/myproj``, make **<SANDENV>** be ``/home/chris/ve/myproj-sandbox``.

The user running the LMS is **<SANDBOX_CALLER>**, for example, you on
your dev machine, or ``www-data`` on a server.

Other details here that depend on your configuration:

1. Create the new virtualenv, using ``--copies`` so that there's a distinct Python executable to limit::

    $ sudo python3.11 -m venv --copies <SANDENV>

   By default, the virtualenv would just symlink against the system Python, and apparmor's default configuration on some operating systems may prevent confinement from being appled to that.

2. (Optional) If you have particular packages you want available to your
   sandboxed code, install them by activating the sandbox virtual env, and
   using pip to install them::

    $ <SANDENV>/bin/pip install -r requirements/sandbox.txt

3. Add a sandbox user::

    $ sudo addgroup sandbox
    $ sudo adduser --disabled-login sandbox --ingroup sandbox

4. Let the web server run the sandboxed Python as sandbox.  Create the file
   ``/etc/sudoers.d/01-sandbox``::

    $ sudo visudo -f /etc/sudoers.d/01-sandbox

    <SANDBOX_CALLER> ALL=(sandbox) SETENV:NOPASSWD:<SANDENV>/bin/python
    <SANDBOX_CALLER> ALL=(sandbox) SETENV:NOPASSWD:/usr/bin/find
    <SANDBOX_CALLER> ALL=(ALL) NOPASSWD:/usr/bin/pkill

   (Note that the ``find`` binary can run arbitrary code, so this is not a safe sudoers file for non-codejail purposes.)

5. Edit an AppArmor profile.  This is a text file specifying the limits on the
   sandboxed Python executable.  The file must be in ``/etc/apparmor.d`` and should
   be named based on the executable, with slashes replaced by dots.  For
   example, if your sandboxed Python is at ``/home/chris/ve/myproj-sandbox/bin/python``,
   then your AppArmor profile must be ``/etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python``.

   See sample profile in ``apparmor-profiles/``. The profile **must be
   customized** to match your sandbox location.

6. Parse the profiles::

    $ sudo apparmor_parser --replace --warn=all --warn=no-debug-cache --Werror <APPARMOR_FILE>

7. Reactivate your project's main virtualenv again.

8. Disable using PAM to set rlimits::

    sed -i '/pam_limits.so/d' /etc/pam.d/sudo

Using CodeJail
--------------

If your CodeJail is properly configured to use safe_exec, try these
commands at your Python terminal::

    import codejail.jail_code
    codejail.jail_code.configure('python', '<SANDENV>/bin/python', user='sandbox')
    import codejail.safe_exec
    jailed_globals = {}
    codejail.safe_exec.safe_exec("output=open('/etc/passwd').read()", jailed_globals)
    print(jailed_globals)  # should be unreachable if codejail is working properly

This should fail with an exception.

If you need to change the packages installed into your sandbox's virtualenv,
you'll need to disable AppArmor, because your sandboxed Python doesn't have
the rights to modify the files in its site-packages directory.

1. Disable AppArmor for your sandbox::

    $ sudo apt-get install apparmor-utils  # if you haven't already
    $ sudo aa-complain /etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python

2. Install or otherwise change the packages installed::

    $ pip install -r requirements/sandbox.txt

3. Re-enable AppArmor for your sandbox::

    $ sudo aa-enforce /etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python


Tests
-----

To run tests, you must perform the standard installation steps. Then
you must set the following environment variables::

    $ export CODEJAIL_TEST_USER=<owner of sandbox (usually 'sandbox')>
    $ export CODEJAIL_TEST_VENV=<SANDENV>

Run the tests with the Makefile::

    $ make tests

Several proxy tests are skipped if proxy mode is not configured.

Design
------

CodeJail is general-purpose enough that it can be used in a variety of projects
to run untrusted code.  It provides two layers:

* ``jail_code.py`` offers secure execution of subprocesses.  It does this by
  running the program in a subprocess managed by AppArmor.

* ``safe_exec.py`` offers specialized handling of Python execution, using
  jail_code to provide the semantics of Python's exec statement.

CodeJail runs programs under AppArmor.  AppArmor is an OS-provided feature to
limit the resources programs can access. To run Python code with limited access
to resources, we make a new virtualenv, then name that Python executable in an
AppArmor profile, and restrict resources in that profile.  CodeJail will
execute the provided Python program with that executable, and AppArmor will
automatically limit the resources it can access.  CodeJail also uses setrlimit
to limit the amount of CPU time and/or memory available to the process.

``codejail.jail_code`` takes a program to run, files to copy into its
environment, command-line arguments, and a stdin stream.  It creates a
temporary directory, creates or copies the needed files, spawns a subprocess to
run the code, and returns the output and exit status of the process.

``codejail.safe_exec`` emulates Python's exec statement.  It takes a chunk of
Python code, and runs it using jail_code, modifying the globals dictionary as a
side-effect.  safe_exec does this by serializing the globals into and out of
the subprocess as JSON.

Limitations
-----------

* If codejail or AppArmor is not configured properly, codejail may default to
  running code insecurely (no sandboxing). It is not secure by default.
  Projects integrating codejail should consider including a runtime test suite
  that checks for proper confinement at startup before untrusted inputs are
  accepted.
* Sandbox isolation is achieved via AppArmor confinement. Codejail facilitates
  this, but cannot isolate execution without the use of AppArmor.
* Resource limits can only be constrained using the mechanisms that Linux's
  rlimit makes available. Some notable deficiencies:

  * While rlimit's ``FSIZE`` can limit the size of any one file that
    a process can create, and can limit the number of files it has open at any
    one time, it cannot limit the total number of files written, and therefore
    cannot limit the total number of bytes written across *all* files.
    A partial mitigation is to constrain the max execution time. (All files
    written in the sandbox will be deleted at end of execution, in any case.)
  * The ``NPROC`` limit constrains the ability of the *current* process to
    create new threads and processes, but the usage count (how many processes
    already exist) is the sum across *all* processes with the same UID, even in
    other containers on the same host where the UID may be mapped to a different
    username. This constraint also applies to the app user due to how the
    rlimits are applied. Even if a UIDs are chosen so they aren't used by other
    software on the host, multiple codejail sandbox processes on the same host
    will share this usage pool and can reduce each other's ability to create
    processes. In this situation, ``NPROC`` will need to be set higher than it
    would be for a single codejail instance taking a single request at a time.

* Sandboxes do not have strong isolation from each other. Under proper
  configuration, untrusted code should not be able to discover other actively
  running code executions, but if this assumption is violated then one sandbox
  could theoretically interfere with another one.

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@openedx.org.
