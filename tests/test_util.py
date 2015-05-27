from githome.util import sanitize_path
import pytest


@pytest.mark.parametrize("path", [
    "/",
    "/.git",
    "foo/bar/.git",
    "/foo/..",
    "..",
    ".",
    # note that absolute paths like /foo/./bar will be collapsed
])
def test_rejects_illegal_paths(path):
    with pytest.raises(ValueError):
        sanitize_path(path)


@pytest.mark.parametrize("path,sane", [
    # basic absolute vs relative and suffix appending
    ("/foo/bar", "foo/bar.git"),
    ("/foo/bar.git", "foo/bar.git"),
    ("foo/bar.git", "foo/bar.git"),
    ("foo/bar", "foo/bar.git"),

    ("fo$o/bar", "fo-o/bar.git"),
    ("fo$o/bar", "fo-o/bar.git"),
    ("foo/$$/bar", "foo/--/bar.git"),
    ("foo/", "foo.git"),
    ("/foo/", "foo.git"),
])
def test_sanitized_paths(path, sane):
    assert str(sanitize_path(path)) == sane
