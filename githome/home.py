from binascii import hexlify
import os
from pathlib import Path
import subprocess
import sys
import uuid

from future.utils import raise_from
import logbook
from sqlacfg import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from .migration import get_upgrade_path
from .model import Base, User, PublicKey, ConfigSetting
from .util import block_update, sanitize_path
from .exc import (UserNotFoundError, KeyNotFoundError, PermissionDenied,
                  NoSuchRepository, GitHomeError)


log = logbook.Logger('githome')


class GitHome(object):
    REPOS_PATH = 'repos'
    DB_PATH = 'githome.sqlite'

    @property
    def dsn(self):
        return 'sqlite:///{}'.format(self.path / self.DB_PATH)

    def __init__(self, path):
        self.path = Path(path)
        self.bind = create_engine(self.dsn)
        self.session = scoped_session(sessionmaker(bind=self.bind))
        self.config = Config(ConfigSetting, self.session)
        self._update_authkeys = False

    def save(self):
        self.session.commit()

        if self._update_authkeys:
            self._update_authkeys = False
            log.critical('missing implementation for _update_authkeys')

            if not self.config['local']['update_authorized_keys']:
                log.info('Not updating authorized_keys, disabled in config')
            else:
                self.update_authorized_keys()

    def create_user(self, name):
        user = User(name=name)
        self.session.add(user)
        return user

    def delete_user(self, name):
        user = self.get_user_by_name(name)
        self.session.delete(user)
        self._update_authkeys = True

        return True

    def iter_users(self, order_by=User.name):
        qry = self.session.query(User)
        if order_by:
            qry = qry.order_by(order_by)

        return qry

    def add_key(self, user, pkey):
        try:
            self.get_key_by_fingerprint(pkey.fingerprint)
        except KeyNotFoundError:
            key = PublicKey.from_pkey(pkey)
        else:
            raise GitHomeError('Key {} already in database'.format(
                pkey.readable_fingerprint
            ))

        key.user = user
        self.session.add(key)

        self._update_authkeys = True
        return pkey

    def delete_key(self, fingerprint):
        self.session.delete(self.get_key_by_fingerprint(fingerprint))
        self._update_authkeys = True

    def get_repo(self, rel_path, create=False):
        path = self.path / self.REPOS_PATH / rel_path

        if not path.exists() or not path.is_dir():
            if create:
                # create the repo
                path.mkdir(parents=True)
                subprocess.check_call([
                    'git', 'init', '--quiet', '--bare',
                    '--shared=0600', str(path),
                ])
            else:
                raise NoSuchRepository('Repository {} no found and not '
                                       'creating.'.format(rel_path))
        return path

    def get_user_by_name(self, name):
        try:
            return self.session.query(User).filter_by(name=name.lower()).one()
        except NoResultFound as e:
            raise_from(UserNotFoundError('User {} not found'.format(name)), e)

    def get_key_by_fingerprint(self, fingerprint):
        try:
            return (self.session.query(PublicKey)
                                .filter_by(fingerprint=hexlify(fingerprint))
                                .one())
        except NoResultFound as e:
            raise_from(KeyNotFoundError('Key {} not found'.format(hexlify
                       (fingerprint))), e)

    def get_authorized_keys_block(self):
        pkeys = []
        for key in self.session.query(PublicKey):
            args = [
                self.config['local']['githome_executable'],
            ]

            args.extend([
                '--githome',
                str(self.path.absolute()),
                'shell',
                key.user.name,
            ])

            full_cmd = ' '.join("'{}'".format(p) for p in args)

            opts = {
                'command': full_cmd,
                'no-agent-forwarding': True,
                'no-port-forwarding': True,
                'no-pty': True,
                'no-user-rc': True,
                'no-x11-forwarding': True,
            }
            pkey = key.as_pkey(options=opts)

            pkeys.append(pkey)

        return '\n'.join(pkey.to_pubkey_line() for pkey in pkeys)

    def update_authorized_keys(self):
        ak = Path(self.config['local']['authorized_keys_file'])
        if not ak.exists():
            log.error('Refusing to update non-existant authorized_keys file: '
                      '{}'.format(ak))
            return

        start_marker = (self.config['local']['authorized_keys_start_marker']
                        .format(self.config['githome']['id']))
        end_marker = (self.config['local']['authorized_keys_start_marker']
                      .format(self.config['githome']['id']))

        old = ak.open().read()

        ak.open('wb').write(block_update(
            start_marker,
            end_marker,
            old,
            self.get_authorized_keys_block(),
        ))
        log.info('Updated {}'.format(ak))

    def authorize_command(self, user, command):
        CMD_WHITELIST = [
            'git-upload-pack',
            'git-receive-pack',
            'git-upload-archive',
        ]

        if not command[0] in CMD_WHITELIST:
            raise PermissionDenied(
                '{} is not a whitelisted command.'.format(command[0])
            )

        if len(command) < 2:
            raise PermissionDenied(
                log.critical('Missing repository parameter')
            )

        # FIXME: check user read rights to repository
        # FIXME: check if user may create repositories
        can_create = False

        repo_path = self.get_repo(sanitize_path(command[1]), create=can_create)
        # FIXME: if necessary, check write rights to repository

        if command[0] == 'git-upload-pack':
            return [command[0], '--strict',   # do not try /.git
                    str(repo_path)]
        elif command[0] == 'git-receive-pack':
            return [command[0], str(repo_path)]
        elif command[0] == 'git-upload-archive':
            return [command[0], str(repo_path)]
        else:
            raise GitHomeError(
                'Command {} is whitelisted, but not explicitly handled.'
                .format(command[0])
            )

    @classmethod
    def check(cls, path):
        """Check if a githome exists at path.

        :param path: A :class:`~pathlib.Path`.
        """
        return (path / cls.DB_PATH).exists()

    @classmethod
    def initialize(cls, path):
        """Initialize new githome at path.

        :param path: A :class:`~pathlib.Path`.
        :param initial_cfg:: Additional configuration settings.
        """
        # create paths
        (path / cls.REPOS_PATH).mkdir()

        # instantiate
        gh = cls(path)

        # create database
        Base.metadata.create_all(bind=gh.bind)

        # create initial configuration
        local = gh.config['local']
        local['update_authorized_keys'] = True
        local['authorized_keys_file'] = os.path.abspath(
            os.path.expanduser('~/.ssh/authorized_keys')
        )
        local['githome_executable'] = str(Path(sys.argv[0]).absolute())
        local['authorized_keys_start_marker'] = (
            '# -- added by githome {}, do not remove these markers --\n'
        )
        local['authorized_keys_end_marker'] = (
            '# -- end githome {}. keep trailing newline! --\n'
        )
        local['use_gh_client'] = True
        gh_client = str(Path(__file__).with_name('gh_client'))
        local['gh_client_executable'] = gh_client
        local['gh_client_socket'] = 'ghclient.sock'

        gh.config['githome']['id'] = str(uuid.uuid4())

        gh.save()

        return gh

    def __repr__(self):
        return '{0.__class__.__name__}(path={0.path!r})'.format(self)

    def get_db_revision(self):
        with self.bind.connect() as con:
            if self.bind.dialect.has_table(con, 'githome_meta'):
                raise NotImplementedError

        return 0

    def upgrade_db(self):
        with self.bind.connect() as con, con.begin() as trans:
            for mfunc in get_upgrade_path(self):
                mfunc(trans)
