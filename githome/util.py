from pathlib import Path
import re


def block_replace(start_marker, end_marker, buf, replacement):
    start = buf.index(start_marker)
    end = buf.index(end_marker, start + len(start_marker))

    return buf[:start + len(start_marker)] + replacement + buf[end:]


def block_update(start_marker, end_marker, buf, content, pad='\n\n'):
    if not buf:
        pad = ''
    try:
        return block_replace(start_marker, end_marker, buf, content)
    except ValueError:
        return buf + pad + start_marker + content + end_marker


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


class ConfigValue(click.ParamType):
    def convert(self, value, param, ctx):
        # type for configuration value given on the command line
        if value.isdigit():
            return int(value)

        if value.lower() in ('on', 'yes', 'true'):
            return True
        elif value.lower() in ('off', 'no', 'false'):
            return False

        return value


class ConfigName(click.ParamType):
    def convert(self, value, param, ctx):
        if not '.' in value:
            raise click.BadParameter('Configuration name must include .')
        return value


class RegEx(click.ParamType):
    def __init__(self, exp):
        super(RegEx, self).__init__()
        self.exp = re.compile(exp)

    def convert(self, value, param, ctx):
        if not self.exp.match(value):
            raise click.BadParameter('Invalid value')
        return value
