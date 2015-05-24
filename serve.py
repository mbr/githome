import trollius as asyncio
from trollius import From


@asyncio.coroutine
def gh_server():
    yield From(asyncio.start_unix_server(gh_proto, 'ux.sock'))


@asyncio.coroutine
def gh_proto(client_reader, client_writer):
    print 'connected'

    while True:
        line = yield From(client_reader.readline())

        if not line:
            break

        print 'line', line[:-1]
        #yield From(client_writer.write('received line: ' + line))


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
