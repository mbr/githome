from binascii import hexlify
from pathlib import Path
import re
import subprocess

import logbook
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .model import Base, User, PublicKey


log = logbook.Logger('githome')


class GitHome(object):
    RESERVED_PATH_COMPONENTS = ('.', '..', '.git')
    INVALID_CHARS_RE = re.compile(r'[^a-zA-Z0-9-_.]')
    SUBSTITUTION_CHAR = '-'

    @staticmethod
    def _make_log_path(path):
        return path / 'log'

    @staticmethod
    def _make_repo_path(path):
        return path / 'repos'

    @staticmethod
    def _make_db_path(path):
        return path / 'githome.sqlite'

    @staticmethod
    def _make_template_path(path):
        return path / 'template'

    @property
    def log_path(self):
        return self._make_log_path(self.path)

    @property
    def repo_path(self):
        return self._make_repo_path(self.path)

    @property
    def db_path(self):
        return self._make_db_path(self.path)

    @property
    def template_path(self):
        return self._make_template_path(self.path)

    @property
    def dsn(self):
        return 'sqlite:///{}'.format(self.db_path)

    def __init__(self, path):
        self.path = Path(path)
        self.bind = create_engine(self.dsn)
        self.session = scoped_session(sessionmaker(bind=self.bind))

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
        safe_path = self.repo_path / Path(*components)

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
        # ensure log path exists
        if not self.log_path.exists():
            self.log_path.mkdir()

        return logbook.RotatingFileHandler(
            str(self.log_path / 'githome.log'),
            **kwargs
        )

    def get_user_by_name(self, name):
        return self.session.query(User).filter_by(name=name.lower()).first()

    def get_key_by_fingerprint(self, fingerprint):
        return self.session.query(PublicKey).get(hexlify(fingerprint))

    @classmethod
    def check(cls, path):
        return cls._make_db_path(path).exists()

    @classmethod
    def initialize(cls, path):
        cls._make_log_path(path).mkdir()
        cls._make_repo_path(path).mkdir()
        cls._make_template_path(path).mkdir()

        gh = cls(path)
        Base.metadata.create_all(bind=gh.bind)

    def __repr__(self):
        return '{0.__class__.__name__}(path={0.path!r})'.format(self)
