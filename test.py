import githome  # for monkey patches

from gevent import spawn
from logbook import StderrHandler
import paramiko

from githome.server import SSHServer
from githome.util import heartbeat, readable_formatter

if __name__ == '__main__':
    spawn(heartbeat)

    handler = StderrHandler()
    handler.formatter = readable_formatter
    with handler.applicationbound():
        SSHServer(paramiko.RSAKey(filename='test_rsa.key')).run()
