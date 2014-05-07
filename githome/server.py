import shlex

from gevent import event, socket, spawn, subprocess, sleep
from gevent.os import nb_read, make_nonblocking
from logbook import Logger
import paramiko

from .util import fmt_addr, fmt_key, ClientLogger


def forward_recv(recv, dest, bufsize=4096):
    while True:
        buf = recv(bufsize)
        if not buf:
            dest.close()
            break
        dest.write(buf)
        dest.flush()


def forward_send(src, sendall):
    fd = src.fileno()
    make_nonblocking(fd)

    while True:
        buf = nb_read(fd, 4096)
        if not buf:
            break

        sendall(buf)


class GitServer(paramiko.ServerInterface):
    def __init__(self, server, client):
        self.event = event.Event()
        self.server = server
        self.client = client
        self.log = ClientLogger('gitserver',
                                client_addr=self.client.getpeername())

    def get_allowed_auths(self, username):
        self.log.debug('Checking allowed auths')
        return 'publickey'

    def check_auth_publickey(self, username, key):
        self.log.warning('No auth checks implemented')
        self.log.debug('user: {}, key: {}'.format(
            username, fmt_key(key)
        ))
        self.log.set_user(username)
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        if not kind == 'session':
            return paramiko.OPEN_FAILED_UNKNOWN_CHANNEL_TYPE
        return paramiko.OPEN_SUCCEEDED

    def check_channel_exec_request(self, channel, command):
        VALID_COMMANDS = [
            'git-receive-pack',
            'git-upload-pack',
            'git-upload-archive',
        ]

        # this is the only kind of channel we allow; executing a command
        cmd = shlex.split(command)

        self.log.debug('{!r} on channel {}'.format(
            cmd, channel.get_id()
        ))

        # check if command is valid
        if not cmd[0] in VALID_COMMANDS:
            self.log.warning('Attempted illegal command: {!r}'.format(cmd))
            return False

        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        p.args = cmd

        spawn(forward_recv, channel.recv, p.stdin),
        spawn(forward_send, p.stdout, channel.sendall),
        spawn(forward_send, p.stderr, channel.sendall_stderr)

        # wait for process completion, close channel afterwards
        spawn(self.cleanup, p, channel)
        return True

    # call cleanup the process asap
    def cleanup(self, p, channel):
        # first, wait for the command to finish
        p.wait()

        # log the return code
        if p.returncode != 0:
            self.log.error('Command {!r} returned error code: {}'.format(
                p.args, p.returncode
            ))

        # yield once, in case some buffers still need to be written
        sleep(0)

        # close the connection
        channel.close()


class SSHServer(object):
    log = Logger('sshserver')

    def __init__(self, host_key, bind='localhost', port=2022, backlog=3):
        self.addr = (bind, port)
        self.backlog = 3
        self.host_key = host_key

    def run(self):
        try:
            self.log.info('Server key fingerprint: {}'.format(
                fmt_key(self.host_key)
            ))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(self.addr)
            sock.listen(self.backlog)

            self.log.info('Listening on {}'.format(fmt_addr(self.addr)))

            while True:
                try:
                    client, addr = sock.accept()
                except socket.error as e:
                    self.log.warning('Could not accept: {}'.format(e))
                else:
                    try:
                        spawn(self.handler, client, addr)
                    except Exception as e:
                        self.log.exceptoin(e)
        except KeyboardInterrupt:
            self.log.info('Exiting...')
        except Exception as e:
            self.log.critical(e)

    def handler(self, client, addr):
        self.log.debug('New connection from {}'.format(fmt_addr(addr)))
        try:
            t = paramiko.Transport(client)
            self.log.debug('DH support: {}'.format(t.load_server_moduli()))
            t.add_server_key(self.host_key)
            server = GitServer(self, client)
            t.start_server(server=server)
        except Exception as e:
            self.log.exception(e)
