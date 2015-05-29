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
from .model import Base, User, PublicKey, ConfigSetting
from .util import block_update, sanitize_path


log = logbook.Logger('githome')


class GitHomeError(Exception):
    pass


class UserNotFoundError(GitHomeError):
    pass


class KeyNotFoundError(GitHomeError):
    pass


class GitHome(object):
    LOG_PATH = 'log'
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

    def get_repo_path(self, unsafe_path, create=False):
        rel_path = sanitize_path(unsafe_path)
        safe_path = self.path / self.REPOS_PATH / sanitize_path(unsafe_path)

        if not safe_path.exists() or not safe_path.is_dir():
            if not create:
                raise ValueError('Repository does not exist')
            log.warning('Creating NEW repository \'{}\' in githome'.format(
                rel_path)
            )

            # create the repo
            safe_path.mkdir(parents=True)
            subprocess.check_call([
                'git', 'init', '--quiet', '--bare',
                '--shared=0600', str(safe_path),
            ])

        return safe_path

    def get_log_handler(self, **kwargs):
        log_path = self.path / self.LOG_PATH
        # ensure log path exists
        if not log_path.exists():
            log_path.mkdir()

        return logbook.RotatingFileHandler(
            str(log_path / 'githome.log'),
            **kwargs
        )

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

    def update_authorized_keys(self, force=False):
        if not self.config['local']['update_authorized_keys'] and not force:
            log.debug('Not updating authorized_keys, disabled in config')
            return

        ak = Path(self.config['local']['authorized_keys_file'])
        if not ak.exists():
            raise RuntimeError('authorized_keys_file does not exist: {}'.
                               format(ak))

        id = self.config['githome']['id']
        start_marker = ('### SECTION ADDED BY GITHOME, DO NOT EDIT\n'
                        '### githome location: {}\n'
                        '### id: {}').format(self.path.absolute(), id)
        end_marker = '### END ADDED BY GITHOME ({})'.format(id)

        old = ak.open().read()

        ak.open('wb').write(block_update(
            start_marker,
            end_marker,
            old,
            self.get_authorized_keys_block(),
        ))
        log.info('Updated {}'.format(ak))

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
        (path / cls.LOG_PATH).mkdir()
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
        gh.config['githome']['id'] = str(uuid.uuid4())

        gh.save()

        return gh

    def __repr__(self):
        return '{0.__class__.__name__}(path={0.path!r})'.format(self)
