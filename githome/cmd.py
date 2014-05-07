import click
from gevent import spawn
from logbook import StderrHandler
import paramiko

from githome.server import SSHServer
from githome.util import heartbeat, readable_formatter


@click.group()
def cli():
    pass


@cli.command()
def server():
    spawn(heartbeat)

    handler = StderrHandler()
    handler.formatter = readable_formatter
    with handler.applicationbound():
        SSHServer(paramiko.RSAKey(filename='test_rsa.key')).run()
