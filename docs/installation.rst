Installation
============

Githome is not entirely fit for public consumption, due to the fact that the
installation process is not well documented yet. To install, the following
things need to happen:

0. Make sure ``git`` is installed.
1. Create a new user account for githome (strictly speaking this is not
   necessary, but this will avoid unpleasant surprises with your own
   ``~/.ssh/authorized_keys`` file). Make sure you create the ``.ssh/``
   directory and ``touch ~/.ssh/authorized_keys``, as githome refuses to update
   these files for security reasons otherwise.
2. Install githome via ``pip``.
3. In an empty directory, run ``githome init``. This will be the top-level home
   of all githome files; repositories will also be stored here.
4. It might be a good idea to inspect the configuration via ``githome config
   show``.
5. Add users and keys. See ``githome --help``.
6. If you are using ``gh_client`` (if ``local.use_gh_client`` is enabled),
   set up your init system to start ``githome server`` (again, see ``--help``).
