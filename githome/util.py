import re


def _update_block(buf, content, start_marker, end_marker):
    BLOCK_RE = re.compile('{}.*?{}'.format(re.escape(start_marker),
                                           re.escape(end_marker)),
                          re.DOTALL)

    block = '\n'.join([start_marker, content, end_marker])

    if BLOCK_RE.search(buf):
        # block is already present
        return BLOCK_RE.sub(buf, block)

    return buf + '\n\n' + block
