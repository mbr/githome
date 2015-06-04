Design
======

How the git client uses SSH
---------------------------

If a user tells git_ to clone, push or pull a remote, the client will connect
via SSH and call the appropriate server command (one of upload-pack_,
receive-pack_ or upload-archive_). These commands make the full repository
available with read- or write access.


githome interception
~~~~~~~~~~~~~~~~~~~~

Upon receiving a connection attempt, OpenSSH_ will consult the authorized_keys_
file for the user account on the server (by convention, a special user named
``git`` is often creating for serving git repositories). Inside the
authorized_keys_ file, it is possible to instruct OpenSSH_ to ignore the
requested command and execute a different one instead; passing on the original
command as an environment variable.

githome modifies the authorized_keys_ file each time a key or user is added and
sets up a line for this specific key. When a connection is made, githome is
called and checks if the user associated with the key that just connected is
allowed to access the repository he requested access to. Any invalid or unknown
commands are rejected as well.

If authorization is granted, githome will replace itself with a call to the
appropriate git server process.


Security
--------

To be as secure as possible with the least amount of work as possible, githome
tries to offload as many security relevant tasks to established software as
possible. The only daemon facing the outside world is OpenSSH_ and to gain any
sort of access, a user must present at least a valid key for any of the
githome user accounts. As long as OpenSSH_ is secure (and configured correctly),
you are safe from unauthorized access from foreign (i.e. *unauthenticated*)
users.

Once a user is authenticated, control is passed over to githome, which
authorizes or denies access based on its own rules: It checks if the user
that is connected has access to the repositories he wants to access. Since any
critical bug in githome here could result in priviledge escalation on
repository access or code execution; githome takes great care to never pass on unknown parameters and uses strictly whitelist-based access to git subsystems.

Once authentication (by OpenSSH_) and authorization (by githome) are done,
githome passes on control to one of the git_ binaries via :func:`~os.execlp`
leaving the rest of the work to be done by git and OpenSSH_.


Performance
-----------

githome was created when I wanted to host git repositories on a `Raspberry Pi 1
<http://raspberrypi.org>`_ and could not coax gitlab_ into to working well
enough on it. Here's why githome runs well on a single core 800 Mhz ARM CPU
System with 512 MB RAM:

* It lets SSH do the heavy crypto lifting. No number crunching is done by
  githome to de- or encrypt stuff.
* :func:`~os.execlp` is used to replace the running githome process with the
  appropriate git binary once all authorization checks have completed. At this
  point no extra in-memory copying is done and things run as if githome had
  never been run as an intermediary.

Two clients
~~~~~~~~~~~

When a user connects via SSH, a client has to be launched to perform githome
authorization. There are two available: ``githome shell`` and ``gh_client``.
The ``githome shell`` functions without any additional setup and will
authenticate the requets itself. It has one drawback: The full python
interpreter and the SQLAlchemy-library must be loaded, which will take up to 5
seconds on a slow SD-card. This feels very slow.

By default, the alternative ``gh_client`` is enabled. It needs a ``githome
server`` to be run to go with it. The server is the heavier python application,
which is meanted to be run as daemon. Upon connection, only ``gh_client``,
which is a very small and fast client written in C needs to be launched. It
will connect to the running server via UNIX domain sockets and wait for an OK
or an authentication error.

If no error occurs, it will execvp_ to the appropriate git server process. The
C client takes only 15 ms to start up on a slow SD card, which is a lot faster.


Alternate design
----------------

githome favored a different architectural approach [1]_ before, using
paramiko_ to deliver a complete SSH-daemon itself instead of using OpenSSH_.
The advantages of this were less "clutter" in the system, no crutches in the
form of hooks to rewrite files like ``.ssh/authorized_keys`` and more fine-
grained control over the process. It also allowed different ways for users to
login, password based logins if desired and the ability assign the same key to
different users.

Ultimately, the approach failed though. While writing the software, some issues
were uncovered with paramiko_. While these could be solved, they made the
author nervous about using it for a critical server implementation. General
paramiko_ development seems to be much more focused on the client side.

As an example, if one follows the sparse docs on key handling, its fairly easy
to confuse the abstract base for public keys with an actual implementation.
Paramiko quietly accepts this, and implement key checking that always compares
empty keys, thus rendering all authentication moot.

To avoid any errors of this kind, githome is for now based on OpenSSH_. This
also reduced complexity quite a bit, as gevent_ or other libraries for parallel
processing were no longer required, avoiding another host of problems.

While the paramiko_-based design is in some ways more interesting, it requires
a lot more effort in auditing and presents a larger attack surface and was
shelved for this reason.


.. [1] Which can be seen up until revision ``fbe3f35``.


.. _gitlab: http://gitlab.com
.. _gevent: http://gevent.org
.. _OpenSSH: http://openssh.com
.. _git: http://git-scm.com
.. _paramiko: http://paramiko.org
.. _receive-pack: http://man7.org/linux/man-pages/man1/git-receive-pack.1.html
.. _upload-pack: http://man7.org/linux/man-pages/man1/git-upload-pack.1.html
.. _upload-archive: http://man7.org/linux/man-pages/man1/git-upload-archive.1.html
.. _authorized_keys: http://man7.org/linux/man-pages/man8/sshd.8.html
.. _execvp: http://man7.org/linux/man-pages/man3/exec.3.html
