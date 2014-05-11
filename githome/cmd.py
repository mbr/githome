import click
import logbook
from logbook import StderrHandler, NullHandler, Logger
import pathlib
import sys

from .home import GitHome
from .model import User, PublicKey
from .util import readable_formatter, fmt_key


@click.group()
@click.option('-d', '--debug/--no-debug', default=False,
              help='Output debugging-level info in logs')
@click.option('--githome', default='.', metavar='PATH', type=pathlib.Path)
@click.pass_context
def cli(ctx, debug, githome):
    log = Logger('cli')

    # setup console logging
    NullHandler().push_application()
    loglevel = logbook.DEBUG if debug else logbook.INFO

    handler = StderrHandler(level=loglevel)
    handler.formatter = readable_formatter
    handler.push_application()

    if debug:
        import logging
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # if we're just calling init, pass to init
    if ctx.invoked_subcommand == 'init':
        return

    # check if the home is valid
    if not GitHome.check(githome):
        log.critical('Not a valid githome: "{}"; use {} init to initialize it'
                     'first.'.format(githome, 'githome'))
        sys.exit(1)

    # create and add to context
    gh = GitHome(githome)
    ctx.obj['githome'] = gh


@cli.group()
def user():
    pass


@user.command('add')
@click.argument('name')
@click.pass_obj
def create_user(obj, name):
    log = Logger('create_user')

    gh = obj['githome']
    if gh.get_user_by_name(name):
        log.critical('User {} already exists'.format(name))
        sys.exit(1)

    user = User(name=name)
    gh.session.add(user)
    gh.session.commit()

    log.info('Created user {}'.format(user.name))


@user.command('delete')
@click.argument('name')
@click.pass_obj
def delete_user(obj, name):
    log = Logger('delete_user')

    gh = obj['githome']

    user = gh.get_user_by_name(name)
    if user:
        gh.session.delete(user)
        gh.session.commit()
        log.info('Removed user {}'.format(user.name))


@user.command('list')
@click.option('-k', '--keys', is_flag=True, default=False)
@click.pass_obj
def list_users(obj, keys):
    gh = obj['githome']

    for user in gh.session.query(User).order_by(User.id):
        line = '{user.id:4d} {user.name:20s}'.format(user=user)

        if keys and user.public_keys:
            line += ' {}'.format(fmt_key(user.public_keys[0].pkey))
        click.echo(line)

        if len(user.public_keys) > 1:
            for key in user.public_keys[1:]:
                click.echo('{0:25s} {}'.format('', fmt_key(key.pkey)))


@cli.group()
def key():
    pass


@key.command('add')
@click.argument('username')
@click.pass_obj
def add_key(obj, username):
    log = Logger('add_key')

    gh = obj['githome']

    user = gh.get_user_by_name(username)

    if not user:
        log.critical('No such user: {}'.format(username))

    log.info('Reading key from stdin...')
    key = PublicKey(data=sys.stdin.read(), user=user)

    gh.session.add(key)
    gh.session.commit()

    log.info('Added key {} for user {}'.format(fmt_key(key.pkey),
                                               key.user.name))


@key.command('remove')
@click.argument('user')
@click.argument('fingerprint')
@click.pass_obj
def remove_key(obj, username):
    log = Logger('remove_key')

    gh = obj['githome']

    #


@cli.command()
@click.argument('path', type=pathlib.Path)
def init(path):
    log = Logger('init')
    if path.exists():
        if [p for p in path.iterdir()]:
            log.critical('Directory {} exists and is not empty'.format(path))
            sys.exit(1)
    else:
        path.mkdir(parents=True)
        log.info('Created {}'.format(path))

    # initialize
    GitHome.initialize(path)
    log.info('Initialized new githome in {}'.format(path))


def run_cli():
    return cli(obj={})
