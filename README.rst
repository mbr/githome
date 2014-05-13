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



.. _gitolite: https://github.com/sitaramc/gitolite
.. _gitosis: https://github.com/tv42/gitosis
.. _git: http://git-scm.com
