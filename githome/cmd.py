import click
from gevent import spawn
import logbook
from logbook import StderrHandler, NullHandler, Logger
import paramiko
import pathlib
import sys

from .home import GitHome
from .server import SSHServer
from .util import heartbeat, readable_formatter


@click.group()
@click.option('-d', '--debug', 'loglevel', default=logbook.INFO,
              flag_value=logbook.DEBUG, is_flag=True,
              help='Output debugging-level info in logs')
@click.option('-D', '--dev', default=False,
              help='Enable development helpers. Do not use in production.')
def cli(loglevel, dev):
    NullHandler().push_application()

    # setup logging (to stdout)
    handler = StderrHandler(level=loglevel)
    handler.formatter = readable_formatter
    handler.push_application()

    if dev:
        spawn(heartbeat)


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
