
import gevent
gevent.monkey.patch_all()

import logging
logging.basicConfig(level=logging.DEBUG)

import argh

from ekimdiscord.main import main

argh.dispatch_command(main)
