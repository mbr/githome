githome
=======

githome is an authorization system for hosting git_ repositories. It allows to
create rules for different users, such as a read-only or developer access and
makes it easy to create new repositories by simply pushing, without having to
prior create them.

githome is somewhat similar to gitolite_, the successor to gitosis_. It aims
to be a little more self-containted and easier to install and administer -
and it's written in Python instead of Perl. The main difference is that it uses
a command-line interface and database to handle settings instead of a git repository, making setups more self-contained and migrateable.

Since it is a security-sensitive piece of software facing the outside world,
detailed information about its structure is found in the documentation, to
help anyone administering it understand the implications on the systems
security.


Installation
------------

To be written.


Security
--------

To be as secure as possible with the least amount of work as possible, githome
tries to offload as many security relevant tasks to established software as
possible. The only daemon facing the outside world is OpenSSH_ and to gain any
sort of access, a user must present at least a valid key for any of the
githome user accounts. As long as OpenSSH_ is secure (and configured correctly),
you are safe from unauthorized access from foreign (i.e. *unknown*) users.

Once a user is authenticated, control is passed over to githome, which
authorizes or denies access based on its own rules: It checks if the user
that is connected has access to the repositories he wants to access. Since any
critical bug in githome here could result in priviledge escalation on
repository access or code execution; githome takes great care to never pass on unknown parameters and uses strictly whitelist-based access to git subsystems.

Once authentication (OpenSSH_) and authorization (githome) are done, githome
passes on control to one of gits commands and removes itself from the process,
leaving the rest of the work to be done by git and OpenSSH_.

Performance
-----------

githome was created when I wanted to host git repositories on a `Raspberry Pi
<http://raspberrypi.org>`_ and even after days of coaxing gitlab_ refused to
work well enough on it. Here's why githome runs well on a single core 800 Mhz
ARM CPU System with 512 MB Ram total:

* It lets SSH do the heavy crypto lifting. No number crunching is done by
  githome to de- or encrypt stuff.
* ``exec`` is used to replace the running githome process with ``git-shell``
  once all authorization checks have completed. At this point, no extra
  in-memory copying is done and things run as if githome had never been used.
* Date that is read often and written rarely is stored in an SQLite db, while
  data that is written often and never read (the logs) is stored in flat
  files.

The worst offense in the performance department is probably that a new
interpreter has to be started up each time a user connects. Cross your fingers
that your OS will dampen the impact of this.

All in all, the overhead of running gitlab is a bit of processing done on each
connect, after that it should perform as if it was never run in the first
place.



Alternate design
----------------

githome favored a different architectural approach[1]_ before, using the
paramiko_ to deliver a complete SSH-daemon instead of using regular SSH. The
advantages of this were less "clutter" in the system, no crutches in the form
of hooks to rewrite files like ``.ssh/authorized_keys`` and more fine-grained
control over the process. It also allowed different ways for users to login,
password based logins if desired and the ability assign the same key to
different users.

Ultimately, the approach failed though. While writing the software I ran into
multiple issues with paramiko_, which could be solved, but made me nervous
about using it for a critical server implementation. As an example, if one
follows the sparse docs on key handling, its fairly easy to confuse the
abstract base for public keys with an actual implementation, which quietly
accepts this, and implement key checking that always compares empty keys, thus
rendering all authentication moot.

This does not say anything about the actual security of paramiko [2]_ -
however, it made me feel that I would need to carefully audit my code and
paramiko's (to ensure I used it correctly), which made the alternative of
basing on OpenSSH with its excellent track record and reputation much more
attractive, at the cost of some functionality.

A good performance also incurred complexity costs on the endeaver with the old
approach, as gevent_ was used and its fairly easy to make mistakes in that
area as well (for example, reusing the random seed, because paramiko_ might
not expect to be run inside greenlets).

All in all, while the paramiko_-based design is a nicer one, it requires a lot
of effort in auditing to get reliable security and was shelved for this
reason.


.. [1] Which can be seen up until revision ``fbe3f35``.
.. [2] I do believe that the focus of paramiko is mainly on SSH clients, as
       its main driving factor seems to be fabric and this shows a bit in
       their documentation and examples.

.. _gitlab: http://gitlab.com
.. _gitolite: https://github.com/sitaramc/gitolite
.. _gitosis: https://github.com/tv42/gitosis
.. _gevent: http://gevent.org
.. _OpenSSH: http://openssh.com
.. _git: http://git-scm.com
