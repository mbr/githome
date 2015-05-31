class GitHomeError(Exception):
    pass


class UserNotFoundError(GitHomeError):
    pass


class KeyNotFoundError(GitHomeError):
    pass


class PermissionDenied(GitHomeError):
    pass


class NoSuchRepository(GitHomeError):
    pass
