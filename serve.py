import os

import logbook
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
        line = (yield From(client_reader.readline())).strip()

        if not line:
            break

        log.debug('arg: {}'.format(line))
        yield From(client_writer.write('received line: ' + line))
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
