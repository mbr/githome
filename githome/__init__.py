# gevent monkey patching, for paramiko and others
from gevent.monkey import patch_all
patch_all()

# redirect paramiko's standard logging to logbook
from logbook.compat import redirect_logging
redirect_logging()
