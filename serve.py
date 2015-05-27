import os

import logbook
from sshkeys import Key as SSHKey
import trollius as asyncio
from trollius import From


log = logbook.Logger('githome-server')


@asyncio.coroutine
def gh_server(socket='ux.sock'):
    if os.path.exists(socket):
        os.unlink(socket)

    yield From(asyncio.start_unix_server(gh_proto, socket))


@asyncio.coroutine
def gh_proto(client_reader, client_writer):
    log = logbook.Logger('client-{}'.format('some-id'))
    log.debug('connected')

    while True:
        keytype = (yield From(client_reader.readline())).strip()
        key = (yield From(client_reader.readline())).strip()

        if not keytype or not key:
            log.warning('incomplete call')
            break

        # check if key is valid
        try:
            pkey = SSHKey.from_pubkey_line('{} {}'.format(keytype, key))
        except Exception:
            log.warning('invalid key')
            yield From(client_writer.write('E invalid public key\n'))
            break

        log.info('{}, {}'.format(pkey.type, pkey.readable_fingerprint))

        if False:
            # check if key is authorized
            yield From(client_writer.write('E access denied\n'))
            break

        yield From(client_writer.write('OK\n'))
        # write OK byte
        yield From(client_writer.write('ls\n'))
        yield From(client_writer.write('foo bar\n'))
        yield From(client_writer.write('foo\n'))
        yield From(client_writer.write('bar\n'))
        yield From(client_writer.write('.'))
        break

    # FIXME: isn't there a better interface for this?
    log.debug('closing connection')
    client_writer._transport.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    # debug
    import logging
    logging.basicConfig()
    loop.set_debug(True)

    server = loop.run_until_complete(gh_server())

    try:
        loop.run_forever()
    finally:
        loop.close()
