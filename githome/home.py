class GitHome(object):
    def __init__(self, path):
        self.path = path

    @property
    def log_path(self):
        return self.path / 'log'

    @property
    def repo_path(self):
        return self.path / 'repos'

    def initialize(self):
        self.log_path.mkdir()
        self.repo_path.mkdir()
