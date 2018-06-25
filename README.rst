CodeJail
========

CodeJail manages execution of untrusted code in secure sandboxes. It is
designed primarily for Python execution, but can be used for other languages as
well.

Security is enforced with AppArmor.  If your operating system doesn't support
AppArmor, then CodeJail won't protect the execution.

CodeJail is designed to be configurable, and will auto-configure itself for
Python execution if you install it properly.  The configuration is designed to
be flexible: it can run in safe mode or unsafe mode.  This helps support large
development groups where only some of the developers are involved enough with
secure execution to configure AppArmor on their development machines.

If CodeJail is not configured for safe execution, it will execute Python
using the same API, but will not guard against malicious code.  This allows the
same code to be used on safe-configured or non-safe-configured developer's
machines.

A CodeJail sandbox consists of several pieces:

#) Sandbox environment. For a Python setup, this would be Python and
   associated core packages. This is denoted throughout this document
   as **<SANDENV>**. This is read-only.

#) Sandbox packages. These are additional packages needed for a given
   run. For example, this might be a grader written by an instructor
   to run over a student's code, or data that a student's code might
   need to access. This is denoted throughout this document as
   **<SANDPACK>**. This is read-only.

#) Untrusted packages. This is typically the code submitted by the
   student to be tested on the server, as well as any data the code
   may need to modify. This is denoted throughout this document as
   **<UNTRUSTED_PACK>**. This is currently read-only, but may need to
   be read-write for some applications.

#) OS packages. These are standard system libraries needed to run
   Python (e.g. things in /lib). This is denoted throughout this
   document as **<OSPACK>**. This is read-only, and is specified by
   Ubuntu's AppArmor profile.

To run, CodeJail requires two user accounts. One account is the main
account under which the code runs, which has access to create
sandboxes. This will be referred to as **<SANDBOX_CALLER>**. The
second account is the account under which the sandbox runs. This is
typically the account 'sandbox.'

Installation
------------

These instructions detail how to configure your operating system so that
CodeJail can execute Python code safely.  You can run CodeJail without these
steps, and you will have an unsafe CodeJail.  This is fine for developers'
machines who are unconcerned with security, and simplifies the integration of
CodeJail into your project.

To secure Python execution, you'll be creating a new virtualenv.  This means
you'll have two: the main virtualenv for your project, and the new one for
sandboxed Python code.

Choose a place for the new virtualenv, call it **<SANDENV>**.

The user running the LMS is **<SANDBOX_CALLER>**, for example, you on
your dev machine, or `www-data` on a server.

Other details here that depend on your configuration:

1. Create the new virtualenv::

    $ sudo virtualenv <SANDENV>

2. Install particular packages you want available to your
   sandboxed code, install them by activating the sandbox virtual env, and
   using pip to install them. For `OPAL` you can find the sandbox-requirements.txt `here <https://github.com/OPAL-Project/codejail/blob/master/sandbox-requirements.txt>`_::

    $ source <SANDENV>/bin/activate
    $ pip install -r sandbox-requirements.txt

3. Add a sandbox user::

    $ sudo addgroup sandbox
    $ sudo adduser --disabled-login sandbox --ingroup sandbox

4. Let the web server run the sandboxed Python as sandbox.  Create the file
   `/etc/sudoers.d/01-sandbox`::

    $ sudo visudo -f /etc/sudoers.d/01-sandbox

    <SANDBOX_CALLER> ALL=(sandbox) SETENV:NOPASSWD:<SANDENV>/bin/python
    <SANDBOX_CALLER> ALL=(sandbox) SETENV:NOPASSWD:/usr/bin/find
    <SANDBOX_CALLER> ALL=(ALL) NOPASSWD:/usr/bin/pkill

  Ensure that when you run <SANDENV>/bin/python, it must run as sandbox user. If this is
  not the case then running below command might give you answers::

    $ sudo -l


5. Install apparmor-profiles::
    
    $ sudo apt-get install apparmor-profiles apparmor-utils


6. Create and edit an AppArmor profile.  This is a text file specifying the limits on the
   sandboxed Python executable.  The file must be in `/etc/apparmor.d` and must
   be named based on the executable, with slashes replaced by dots.  For
   example, if your sandboxed Python binary (not symlinks) is at `/home/chris/ve/myproj-sandbox/bin/python`,
   then your AppArmor profile generated will be `/etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python`::

    $ sudo aa-genprof /home/chris/ve/myproj-sandbox/bin/python  # generate apparmor profile

    $ sudo vim /etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python

    #include <tunables/global>

    <SANDENV>/bin/python {
        # edit begins here
        #include <abstractions/base>
        #include <abstractions/python>

        <SANDENV>/** mr,
        # If you have code that the sandbox must be able to access, add lines
        # pointing to those directories:
        /the/path/to/your/sandbox-packages/** r,

        /tmp/codejail-*/ rix,
        /tmp/codejail-*/** wrix,
    }

7. Parse the profiles::

    $ sudo apparmor_parser <APPARMOR_FILE>

8. Reactivate your project's main virtualenv again.

Using CodeJail
--------------

If your CodeJail is properly configured to use safe_exec, try these
commands at your Python terminal:

.. code:: python

    import codejail
    jail = codejail.configure('python', '<SANDENV>/bin/python')
    jail = codejail.get_codejail('python')  # this works anytime after configuration has happened
    jail.safe_exec("import os\nos.system('ls /etc')", {})

This should fail with a SafeExecException.  Similarly, the following will
return a JailResult indicating that an exception was raised:

.. code:: python

    result = jail.jail_code("import os\nos.system('ls /etc')")
    assert result.status != 0
    assert result.stdout == ''
    assert 'Error' in result.stderr

If you need to change the packages installed into your sandbox's virtualenv,
you'll need to disable AppArmor, because your sandboxed Python doesn't have
the rights to modify the files in its site-packages directory.

1. Disable AppArmor for your sandbox::

    $ sudo apt-get install apparmor-utils  # if you haven't already
    $ sudo aa-complain /etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python

2. Install or otherwise change the packages installed::

    $ pip install -r sandbox-requirements.txt

3. Re-enable AppArmor for your sandbox::

    $ sudo aa-enforce /etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python


Tests
-----

Run the tests with the Makefile::

    $ make tests

If CodeJail is running unsafely, many of the tests will be automatically
skipped, or will fail, depending on whether CodeJail thinks it should be in
safe mode or not.


Design
------

CodeJail is general-purpose enough that it can be used in a variety of projects
to run untrusted code.  It provides two layers:

* ``codejail.Jail.jail_code()`` offers secure execution of subprocesses.  It does this by
  running the program in a subprocess managed by AppArmor.

  This takes a program to run, files to copy into its environment, command-line
  arguments, and a stdin stream.  It creates a temporary directory, creates or
  copies the needed files, spawns a subprocess to run the code, and returns the
  output and exit status of the process.

.. image:: https://raw.githubusercontent.com/edx/codejail/master/doc/jail_code.png
    :alt: Data flow when running Jail.jail_code()
    :width: 800px

* ``codejail.Jail.safe_exec()`` offers specialized handling of Python execution, using
  jail_code to provide the semantics of Python's exec statement.

  This emulates Python's exec statement.  It takes a chunk of Python code, and
  runs it using jail_code, modifying the globals dictionary as a side-effect.
  safe_exec does this by serializing the globals into and out of the subprocess
  run by ``codejail.Jail.jail_code()`` as JSON.

.. image:: https://raw.githubusercontent.com/edx/codejail/master/doc/safe_exec.png
    :alt: Data flow when running Jail.safe_exec()
    :width: 800px

CodeJail runs programs under AppArmor.  AppArmor is an OS-provided feature to
limit the resources programs can access. To run Python code with limited access
to resources, we make a new virtualenv, then name that Python executable in an
AppArmor profile, and restrict resources in that profile.  CodeJail will
execute the provided Python program with that executable, and AppArmor will
automatically limit the resources it can access.  CodeJail also uses setrlimit
to limit the amount of CPU time and/or memory available to the process.

For backwards compatibility, the methods ``codejail.Jail.jail_code`` and
``codejail.Jail.safe_exec`` are also available as functions
(``codejail.jail_code.jail_code`` and ``codejail.safe_exec.safe_exec``) that take
in an extra argument which is a string naming the configured Jail object
(``"python"`` in the above examples).
