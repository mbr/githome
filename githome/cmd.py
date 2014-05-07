import click
from gevent import spawn
import logbook
from logbook import StderrHandler, NullHandler, Logger
import paramiko
import pathlib
import sys

from .home import GitHome
from .server import SSHServer
from .util import heartbeat as hb, readable_formatter


@click.group()
@click.option('-d', '--debug/--no-debug', default=False,
              help='Output debugging-level info in logs')
@click.option('--heartbeat', default=False, is_flag=True,
              help='Enable heartbeat in logs. Only used in development.')
def cli(debug, heartbeat):
    NullHandler().push_application()

    loglevel = logbook.DEBUG if debug else logbook.INFO

    # setup logging (to stdout)
    handler = StderrHandler(level=loglevel)
    handler.formatter = readable_formatter
    handler.push_application()

    if debug:
        import logging
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    if heartbeat:
        spawn(hb)


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
