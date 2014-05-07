from sqlalchemy import create_engine

from .model import Base


class GitHome(object):
    def __init__(self, path):
        self.path = path

    @property
    def log_path(self):
        return self.path / 'log'

    @property
    def repo_path(self):
        return self.path / 'repos'

    @property
    def db_path(self):
        return self.path / 'githome.sqlite'

    @property
    def dsn(self):
        return 'sqlite:///{}'.format(self.db_path)

    def create_engine(self, echo=False):
        return create_engine(self.dsn, echo=echo)

    def initialize(self, echo=False):
        self.log_path.mkdir()
        self.repo_path.mkdir()

        engine = self.create_engine(echo=echo)
        Base.metadata.create_all(bind=engine)
