import click
import logbook
from logbook import StderrHandler, NullHandler, Logger
import paramiko
import pathlib
import sys

from .home import GitHome
from .model import User
from .server import SSHServer
from .util import readable_formatter


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


@user.command('create')
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
@click.pass_obj
def list_users(obj):
    gh = obj['githome']

    for user in gh.session.query(User).order_by(User.id):
        print '{user.id:4d} {user.name}'.format(user=user)


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
    gh = GitHome(path)
    gh.initialize()
    log.info('Initialized new githome in {}'.format(path))


@cli.command()
def server():
    SSHServer(paramiko.RSAKey(filename='test_rsa.key')).run()


def run_cli():
    return cli(obj={})
