
import gevent.monkey
# aiogevent is not compatible with patched threading
gevent.monkey.patch_all(thread=False)

import logging
logging.basicConfig(level=logging.DEBUG)

import argh

from ekimdiscord.main import main

argh.dispatch_command(main)
