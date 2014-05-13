Design
======

How it works
------------

In general, if any user tells git_ via SSH to clone, push or pull a
repository, the latter will connect via SSH and call the appropriate server
command (one of upload-pack_, receive-pack_ or upload-archive_).

Upon receiving this connection, OpenSSH_ will consult the authorized_keys_ file
for the user account on the server (by convention, often ``git``), ignore the
requested command and execute githome instead, passing on the original command
as a parameter and the user account as identified by its key. For this to work,
githome modifies ``~/.ssh/authorized_keys`` every time a key or user of a
githome is removed or added.

Githome will inspect the comment, check if the user is allowed to do so and
either exit with an error message if the remote user has insufficient
permissions; or call the necessary git_ binary to handle the request.


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

Once authentication (OpenSSH_) and authorization (githome) are done, githome
passes on control to one of the git_ binaries via :func:`~os.execlp` leaving
the rest of the work to be done by git and OpenSSH_.


Performance
-----------

githome was created when I wanted to host git repositories on a `Raspberry Pi
<http://raspberrypi.org>`_ and could not coax gitlab_ into to working well
enough on it. Here's why githome runs well on a single core 800 Mhz ARM CPU
System with 512 MB RAM:

* It lets SSH do the heavy crypto lifting. No number crunching is done by
  githome to de- or encrypt stuff.
* :func:`~os.execlp` is used to replace the running githome process with the
  appropriate git binary once all authorization checks have completed. At this
  point no extra in-memory copying is done and things run as if githome had never
  been run as an intermediary.
* Date that is read often and written rarely is stored in an SQLite database,
  while data that is written often and never read (the logs) is stored in flat
  files.

The worst offense in the performance department is starting up Python each
time a user connects, which is tolerable.


Alternate design
----------------

githome favored a different architectural approach [1]_ before, using
paramiko_ to deliver a complete SSH-daemon itself instead of using OpenSSH_.
The advantages of this were less "clutter" in the system, no crutches in the
form of hooks to rewrite files like ``.ssh/authorized_keys`` and more fine-
grained control over the process. It also allowed different ways for users to
login, password based logins if desired and the ability assign the same key to
different users.

Ultimately, the approach failed though. While writing the software I ran into
some issues with paramiko_, which could be solved, but made me nervous
about using it for a critical server implementation (development on it seems to be much more focused on the client side). As an example, if one
follows the sparse docs on key handling, its fairly easy to confuse the
abstract base for public keys with an actual implementation, which quietly
accepts this, and implement key checking that always compares empty keys, thus
rendering all authentication moot.

To avoid shooting myself in the foot in any way, I decided to base the project
on OpenSSH_ after all, including its excellent track record and reputation, at
the cost of some functionality.

This also reduced complexity quite a bit, as gevent_ or other libraries for parallel processing were no longer reqruired, avoiding another host of
problems.

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
