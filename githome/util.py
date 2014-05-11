from binascii import hexlify

from logbook import Logger
from logbook.handlers import DEFAULT_FORMAT_STRING


class ClientLogger(Logger):
    def __init__(self, *args, **kwargs):
        self.extras = {
            'client_addr': kwargs.pop('client_addr')
        }
        super(ClientLogger, self).__init__(*args, **kwargs)

    def set_user(self, user):
        self.extras['user'] = user

    def handle(self, record):
        # attach client_addr
        record.extra.update(self.extras)
        return super(ClientLogger, self).handle(record)


FORMAT_STRING_WITH_CLIENT = (
    '[{record.time:%Y-%m-%d %H:%M}] {record.level_name}: {record.channel}: '
    '[{client}] {record.message}'
)


def readable_formatter(record, handler):
    client_addr = record.extra.get('client_addr', None)
    user = record.extra.get('user', None)

    client = None
    if client_addr:
        client = fmt_addr(client_addr)

        if user:
            client += '/{}'.format(user)

    if client:
        return FORMAT_STRING_WITH_CLIENT.format(record=record, client=client)
    else:
        return DEFAULT_FORMAT_STRING.format(record=record)


def batch_str(n, s):
    for i in xrange(0, len(s), n):
        yield s[i:i+n]


def fmt_key(key):
    return ':'.join(batch_str(2, hexlify(key.get_fingerprint())))


def fmt_addr(addr):
    return '{}:{}'.format(*addr)
