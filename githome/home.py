from binascii import hexlify
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import logbook
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .model import Base, User, PublicKey, ConfigSetting
from .util import _update_block


log = logbook.Logger('githome')


class GitHome(object):
    RESERVED_PATH_COMPONENTS = ('.', '..', '.git')
    INVALID_CHARS_RE = re.compile(r'[^a-zA-Z0-9-_.]')
    SUBSTITUTION_CHAR = '-'

    LOG_PATH = 'log'
    REPOS_PATH = 'repos'
    DB_PATH = 'githome.sqlite'
    TEMPLATE_PATH = 'template'

    @property
    def dsn(self):
        return 'sqlite:///{}'.format(self.path / self.DB_PATH)

    def __init__(self, path):
        self.path = Path(path)
        self.bind = create_engine(self.dsn)
        self.session = scoped_session(sessionmaker(bind=self.bind))

    def get_config(self, key):
        cs = self.session.query(ConfigSetting).get(key)
        return None if cs is None else cs.value

    def set_config(self, key, value):
        cs = self.session.query(ConfigSetting).get(key)
        if cs is None:
            raise KeyError(key)
        cs.value = value
        self.session.add(cs)

    def get_repo_path(self, unsafe_path, create=False):
        unsafe = Path(unsafe_path)

        # turn any absolute unsafe path into a relative one
        if unsafe.is_absolute():
            unsafe_comps = unsafe.parts[1:]
        else:
            unsafe_comps = unsafe.parts

        # every component must be alphanumeric
        components = []
        for p in unsafe_comps:
            # disallow .git
            if p.endswith('.git'):
                raise ValueError('Cannot end path in .git')

            # remove invalid characters
            clean = self.INVALID_CHARS_RE.sub(self.SUBSTITUTION_CHAR, p)

            # if the name is empty, reject it
            if not p:
                raise ValueError('Path component too short.')

            # if the name is potentially dangerous, reject it
            if p in self.RESERVED_PATH_COMPONENTS:
                raise ValueError('{} is a reserved path component.'.format(p))

            components.append(clean)

        if not components:
            raise ValueError('Path too short')

        # append a final .git
        user_path = Path(*components)  # used only for printing

        components[-1] += '.git'
        safe_path = self.path / self.REPOS_PATH / Path(*components)

        if not safe_path.exists() or not safe_path.is_dir():
            if not create:
                raise ValueError('Repository does not exist')
            log.warning('Creating NEW repository \'{}\' in githome'.format(
                user_path)
            )

            # create the repo
            safe_path.mkdir(parents=True)
            subprocess.check_call([
                'git', 'init', '--quiet', '--bare',
                '--shared=0600', str(safe_path),
                '--template', str(self.template_path),
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
        return self.session.query(User).filter_by(name=name.lower()).first()

    def get_key_by_fingerprint(self, fingerprint):
        return self.session.query(PublicKey).get(hexlify(fingerprint))

    def get_authorized_keys_block(self, debug=False):
        pkeys = []
        for key in self.session.query(PublicKey):
            args = [
                self.get_config('githome_executable'),
            ]

            if debug:
                args.append('--debug')

            args.extend([
                '--githome',
                str(self.path.absolute()),
                '--remote',
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
        if not self.get_config('update_authorized_keys') and not force:
            log.debug('Not updating authorized_keys, disabled in config')
            return

        ak = Path(self.get_config('authorized_keys_file'))
        if not ak.exists():
            raise RuntimeError('authorized_keys_file does not exist: {}'.
                               format(ak))

        id = self.get_config('githome_id')
        start_marker = ('### SECTION ADDED BY GITHOME, DO NOT EDIT\n'
                        '### githome location: {}\n'
                        '### id: {}').format(self.path.absolute(), id)
        end_marker = '### END ADDED BY GITHOME ({})'.format(id)

        old = ak.open().read()

        ak.open('wb').write(_update_block(
            old,
            self.get_authorized_keys_block(),
            start_marker,
            end_marker,
        ))
        log.info('Updated {}'.format(ak))

    @classmethod
    def check(cls, path):
        return cls._make_db_path(path).exists()

    @classmethod
    def initialize(cls, path):
        (path / cls.LOG_PATH).mkdir()
        (path / cls.REPOS_PATH).mkdir()
        (path / cls.TEMPLATE_PATH).mkdir()

        gh = cls(path)
        Base.metadata.create_all(bind=gh.bind)

        # create initial configuration
        cfgs = {
            'update_authorized_keys': True,
            'authorized_keys_file': os.path.abspath(os.path.expanduser(
                '~/.ssh/authorized_keys')),
            'githome_executable': str(Path(sys.argv[0]).absolute()),
            'githome_id': str(uuid.uuid4()),
        }

        for k, v in cfgs.items():
            gh.session.add(ConfigSetting(key=k, value=v))
        gh.session.commit()

        return gh

    def __repr__(self):
        return '{0.__class__.__name__}(path={0.path!r})'.format(self)
