from binascii import hexlify

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .model import Base, User, PublicKey


class GitHome(object):
    @staticmethod
    def _make_log_path(path):
        return path / 'log'

    @staticmethod
    def _make_repo_path(path):
        return path / 'repos'

    @staticmethod
    def _make_db_path(path):
        return path / 'githome.sqlite'

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
    def dsn(self):
        return 'sqlite:///{}'.format(self.db_path)

    def __init__(self, path):
        self.path = path
        self.bind = create_engine(self.dsn)
        self.session = scoped_session(sessionmaker(bind=self.bind))

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

        gh = cls(path)
        Base.metadata.create_all(bind=gh.bind)

    def __repr__(self):
        return '{0.__class__.__name__}(path={0.path!r})'.format(self)
