from pathlib import Path
import re


def _update_block(buf, content, start_marker, end_marker):
    BLOCK_RE = re.compile('{}.*?{}'.format(re.escape(start_marker),
                                           re.escape(end_marker)),
                          re.DOTALL)

    block = '\n'.join([start_marker, content, end_marker])

    if BLOCK_RE.search(buf):
        # block is already present
        return BLOCK_RE.sub(buf, block)

    return buf + '\n\n' + block


def sanitize_path(path, subchar='-', invalid_chars=r'[^a-zA-Z0-9-_.]',
                  invalid_comps=('.', '..', '.git'), force_suffix='.git'):
    """Sanitizes a path by making it relative and git safe.

    Any part coming in will be made relative first (by cutting leading
    slashes). Invalid characters (see ``invalid_chars``) are removed and
    replaced with ``subchar``. A suffix can be forced upon the path as well.

    :param path: Path to sanitize (string or Path).
    :param subchar: Character used to substitute illegal path components with.
    :param invalid_chars: A regular expression that matches invalid characters.
    :param invalid_comps: A collection of path components that are not allowed.
    :param force_suffix: The suffix to force onto each path.
    :return: A Path instance denoting a relative path.
    """
    unsafe = Path(path)

    # turn absolute path into a relative one by stripping the leading '/'
    if unsafe.is_absolute():
        unsafe = unsafe.relative_to(unsafe.anchor)

    # every component must be alphanumeric
    components = []
    for p in unsafe.parts:
        # remove invalid characters
        clean = re.sub(invalid_chars, subchar, p)

        # if the name is empty, ignore it. this usually shouldn't happend with
        # pathlib
        if not clean:
            continue

        # if the name is potentially dangerous, reject it
        if clean in invalid_comps:
            raise ValueError('{} is a reserved path component'.format(clean))

        components.append(clean)

    if not components:
        raise ValueError('Path too short')

    # append a final suffix if not present
    if force_suffix and not components[-1].endswith(force_suffix):
        components[-1] += force_suffix

    return Path(*components)
