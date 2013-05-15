CodeJail
========

CodeJail manages execution of untrusted code in secure sandboxes. It is
designed primarily for Python execution, but can be used for other languages as
well.

Security is enforced with AppArmor.  If your operating system doesn't support
AppArmor, then CodeJail won't protect the execution.

CodeJail is designed to be configurable, and will auto-configure itself for
Python execution if you install it properly.  The configuration is designed to
be flexible: it can run in safe more or unsafe mode.  This helps support large
development groups where only some of the developers are involved enough with
secure execution to configure AppArmor on their development machines.

If CodeJail is not configured for safe execution, it will execution Python
using the same API, but will not guard against malicious code.  This allows the
same code to be used on safe-configured or non-safe-configured developer's
machines.


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

Choose a place for the new virtualenv, call it <SANDENV>.  It will be
automatically detected and used if you put it right alongside your existing
virtualenv, but with `-sandbox` appended.  So if your existing virtualenv is in
`/home/chris/ve/myproj`, make <SANDENV> be `/home/chris/ve/myproj-sandbox`.

Other details here that depend on your configuration:

    - The user running the LMS is <WWWUSER>, for example, you on your dev
      machine, or `www-data` on a server.

1. Create the new virtualenv::

    $ sudo virtualenv <SANDENV>

2. (Optional) If you have particular packages you want available to your
   sandboxed code, install them by activating the sandbox virtual env, and
   using pip to install them::

    $ source <SANDENV>/bin/activate
    $ sudo pip install -r sandbox-requirements.txt

3. Add a sandbox user::

    $ sudo addgroup sandbox
    $ sudo adduser --disabled-login sandbox --ingroup sandbox

4. Let the web server run the sandboxed Python as sandbox.  Create the file
   `/etc/sudoers.d/01-sandbox`::

    $ visudo -f /etc/sudoers.d/01-sandbox

    <WWWUSER> ALL=(sandbox) NOPASSWD:<SANDENV>/bin/python

5. Edit an AppArmor profile.  This is a text file specifying the limits on the
   sandboxed Python executable.  The file must be in `/etc/apparmor.d` and must
   be named based on the executable, with slashes replaced by dots.  For
   example, if your sandboxed Python is at `/home/chris/ve/myproj-sandbox/bin/python`,
   then your AppArmor profile must be `/etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python`::

    $ sudo vim /etc/apparmor.d/home.chris.ve.myproj-sandbox.bin.python

    #include <tunables/global>

    <SANDENV>/bin/python {
        #include <abstractions/base>

        <SANDENV>/** mr,
        # If you have code that the sandbox must be able to access, add lines
        # pointing to those directories:
        /the/path/to/your/sandbox-packages/** r,

        /tmp/codejail-*/ rix,
        /tmp/codejail-*/** rix,
    }

6. Parse the profiles::

    $ sudo apparmor_parser <APPARMOR_FILE>

7. Reactivate your project's main virtualenv again.


Tests
=====

The tests run under nose in the standard fashion.

If CodeJail is running unsafely, many of the tests will be automatically
skipped, or will fail, depending on whether CodeJail thinks it should be in
safe mode or not.
