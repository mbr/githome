import logbook
import logging
import pathlib
import os
import shlex
import sys

import click
from logbook import StderrHandler, NullHandler, Logger
from logbook.compat import redirect_logging
from sqlacfg.format import ini_format
from sshkeys import Key as SSHKey

from .home import GitHome
from .model import User, PublicKey, ConfigSetting


log = Logger('cli')


def abort(status=1):
    sys.exit(status)


@click.group()
@click.option('-d', '--debug', 'loglevel', flag_value=logbook.DEBUG)
@click.option('-q', '--quiet', 'loglevel', flag_value=logbook.WARNING)
@click.option('--githome', default='.', metavar='PATH', type=click.Path())
@click.pass_context
def cli(ctx, githome, loglevel):
    ctx.obj = {}

    if loglevel is None:
        loglevel = logbook.INFO

    # setup sqlalchemy loglevel
    if loglevel is logging.DEBUG:
        redirect_logging()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # setup console logging
    NullHandler().push_application()
    StderrHandler(level=loglevel).push_application()

    ctx.obj['githome_path'] = pathlib.Path(githome)

    # if we're just calling init, do not initialize githome
    if ctx.invoked_subcommand == 'init':
        return

    # check if the home is valid
    if not GitHome.check(githome):
        log.critical('Not a valid githome: "{}"; use {} init to initialize it '
                     'first.'.format(githome, 'githome'))
        abort(1)

    # create and add to context
    gh = GitHome(ctx.obj['githome_path'])
    ctx.obj['githome'] = gh

    # log to file in githome
    gh.get_log_handler(level=loglevel, bubble=True).push_application()


@cli.command()
@click.argument('username')
@click.pass_obj
def shell(obj, username):
    log = Logger('githome-shell')

    gh = obj['githome']

    # get user
    user = gh.get_user_by_name(username)

    if not user:
        log.critical('Invalid user: {}'.format(username))
        abort(1)

    log.info('Shell auth from: {}.'.format(user.name))
    log = Logger('githome-shell [{}]'.format(user.name))

    # we've got our user, now authorize him or not
    # FIXME: missing any sort of authorization system

    shell_cmd = shlex.split(os.environ.get('SSH_ORIGINAL_COMMAND', ''))
    log.debug('SSH_ORIGINAL_COMMAND {!r}'.format(shell_cmd))

    CMD_WHITELIST = [
        'git-upload-pack',
        'git-receive-pack',
        'git-upload-archive',
    ]

    if not shell_cmd:
        log.critical('No shell command given')
        abort(1)

    if not shell_cmd[0] in CMD_WHITELIST:
        log.critical('{} is not a whitelisted command.'.format(shell_cmd[0]))
        abort(1)

    if len(shell_cmd) < 2:
        log.critical('Missing repository parameter')
        abort(2)

    try:
        repo_path = gh.get_repo_path(shell_cmd[1], create=True)
    except ValueError as e:
        log.critical('Bad repository ({}): {}'.format(shell_cmd[1], e))
        abort(1)

    if shell_cmd[0] == 'git-upload-pack':
        safe_args = [shell_cmd[0], '--strict',   # enforce strict
                     str(repo_path)]
    elif shell_cmd[0] == 'git-receive-pack':
        safe_args = [shell_cmd[0], str(repo_path)]
    elif shell_cmd[0] == 'git-upload-archive':
        safe_args = [shell_cmd[0], str(repo_path)]
    else:
        log.critical('Command {} is whitelisted, but not explicitly handled.'
                     .format(shell_cmd[0]))
        abort(1)

    log.debug('Repository path is {}'.format(repo_path))

    log.debug('Executing {!r}', safe_args)
    binary = safe_args[0]  # we use path through execlP
    os.execlp(binary, *safe_args)


@cli.command()
@click.option('--cmd', default=None,
              help='Path to executable for githome.')
@click.pass_obj
def authorized_keys(obj, cmd):
    gh = obj['githome']

    click.echo(gh.get_authorized_keys_block(obj['debug']))


@cli.group('user')
def user_group():
    pass


@user_group.command('add')
@click.argument('name')
@click.pass_obj
def create_user(obj, name):
    gh = obj['githome']
    if gh.get_user_by_name(name):
        log.critical('User {} already exists'.format(name))
        abort(1)

    user = User(name=name)
    gh.session.add(user)
    gh.session.commit()

    log.info('Created user {}'.format(user.name))


@user_group.command('delete')
@click.argument('name')
@click.pass_obj
def delete_user(obj, name):
    gh = obj['githome']

    user = gh.get_user_by_name(name)
    if user:
        gh.session.delete(user)
        gh.session.commit()
        log.info('Removed user {}'.format(user.name))

        gh.update_authorized_keys()


@user_group.command('list')
@click.option('-k', '--keys', is_flag=True, default=False)
@click.pass_obj
def list_users(obj, keys):
    gh = obj['githome']

    for user in gh.session.query(User).order_by(User.id):
        line = '{user.id:4d} {user.name:20s}'.format(user=user)

        if keys and user.public_keys:
            line += ' * {}'.format(
                user.public_keys[0].as_pkey().readable_fingerprint
            )
        click.echo(line)

        if len(user.public_keys) > 1 and keys:
            for key in user.public_keys[1:]:
                click.echo('{0:25s} * {1}'.format(
                    '', key.as_pkey().readable_fingerprint
                ))


@cli.group('key')
def key_group():
    pass


@key_group.command('add')
@click.argument('username')
@click.argument('keyfiles', type=click.File('rb'), nargs=-1)
@click.pass_obj
def add_key(obj, username, keyfiles):
    gh = obj['githome']

    user = gh.get_user_by_name(username)

    if not user:
        log.critical('No such user: {}'.format(username))
        abort(1)

    for keyfile in keyfiles:
        for line in keyfile:
            line = line.strip()
            if not line:
                continue

            pkey = SSHKey.from_pubkey_line(line)
            _k = gh.get_key_by_fingerprint(pkey.fingerprint)
            if _k:
                log.warning('Key {} ignored, already registered for {}'.format(
                    pkey.readable_fingerprint, _k.user.name
                ))
                continue

            log.info('Adding key {} to user {}...'.format(
                pkey.readable_fingerprint, user.name)
            )
            k = PublicKey.from_pkey(pkey)
            k.user = user
            gh.session.add(k)

    gh.session.commit()

    gh.update_authorized_keys()


@key_group.command('remove')
@click.argument('fingerprints', nargs=-1)
@click.pass_obj
def remove_key(obj, fingerprints):
    gh = obj['githome']

    for fingerprint in fingerprints:
        key = gh.get_key_by_fingerprint(fingerprint.replace(':', ''))

        if not key:
            log.warning('Key {} not found.'.format(fingerprint))
            continue

    if fingerprints:
        gh.update_authorized_keys()


@key_group.command('list')
@click.pass_obj
def list_keys(obj):
    gh = obj['githome']

    for key in gh.session.query(PublicKey).order_by(PublicKey.user_id):
        click.echo('{} ({})'.format(
            key.as_pkey().readable_fingerprint, key.user.name
        ))


@cli.group('config')
def config_group():
    pass


@config_group.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_obj
def set_config(obj, key, value):
    gh = obj['githome']

    try:
        gh.set_config(key, value)
    except KeyError:
        log.critical('No such configuration value: {}'.format(key))
        abort(1)
    gh.session.commit()

    log.info('Configuration set: {}={}'.format(key, value))


@config_group.command('list')
@click.pass_obj
def list_config(obj):
    gh = obj['githome']

    for cs in gh.session.query(ConfigSetting):
        click.echo('{cs.key:25s} {cs.value}'.format(cs=cs))


@cli.command()
@click.pass_obj
def init(obj):
    path = obj['githome_path']

    if path.exists():
        if [p for p in path.iterdir()]:
            log.critical('Directory {} exists and is not empty'.format(path))
            abort(1)
    else:
        path.mkdir(parents=True)
        log.info('Created {}'.format(path))

    # initialize
    gh = GitHome.initialize(path)
    log.info('Initialized new githome in {}.'.format(path))
    log.info('Configuration:\n{}'.format(ini_format(gh.config)))
