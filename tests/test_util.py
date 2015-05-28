from githome.util import sanitize_path, block_replace
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


@pytest.mark.parametrize("start,end", [
    ("smallstart", "smallend"),
    ("LARGESTART" * 64, "LARGEEND" * 64),
    ("witha\n" * 64, "linebreak\n" * 64),
])
def test_block_replace(start, end):
    buf = 'sample data\n\n' + start + 'foo\n' + end + 'xyz'
    buf2 = 'sample data\n\n' + start + 'bar\n' + end + 'xyz'

    assert buf2 == block_replace(buf, 'bar\n', start, end)


def test_block_replace_sample_block():
    before = """
this is a of block replace

blabla

### BEGIN ###
stuff goes here
and here
### END ###

footer
"""

    after = """
this is a of block replace

blabla

### BEGIN ###
new contents
### END ###

footer
"""

    assert block_replace(before,
                         'new contents\n',
                         '### BEGIN ###\n',
                         '### END ###\n') == after


def test_empty_block_replace():
    assert block_replace('foobar', '!!', 'foo', 'bar') == 'foo!!bar'


def test_block_replace_not_found():
    with pytest.raises(ValueError):
        block_replace('foobar', '!!', '#', '#')


def test_overlapping_block_replace_fails():
    with pytest.raises(ValueError):
        assert block_replace('###', 'x', '##', '##')


def test_block_replace_only_replaces_first():
    assert (block_replace('fooxbaryfoozbar', '!!', 'foo', 'bar') ==
            'foo!!baryfoozbar')
