
import asyncio
import logging
import os

import aiogevent
import discord
import gevent.pool
from discord.enums import MessageType

import escapes
import lineedit

from .config import Config

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"


class EkimDiscord(object):

	def __init__(self, configpath, token):
		self.group = gevent.pool.Group()
		self.config = Config(configpath)
		self.token = token
		self.editor = lineedit.LineEditing(
			input_fn=lineedit.gevent_read_fn, gevent_handle_sigint=True
		)
		self.client = discord.Client()

		@self.client.event
		async def on_message(message):
			return await aiogevent.wrap_greenlet(self.group.spawn(self.on_message, message))


	def run(self):
		editor_log_handler = lineedit.LoggingHandler(self.editor)
		editor_log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
		self._input_looper = self.group.spawn(self.input_loop)
		with self.editor, editor_log_handler:
			# blocks until client quit
			asyncio.get_event_loop().run_until_complete(self.client.start(self.token, bot=False))


	def on_message(self, message):
		self.editor.write(self.format_message(message))


	def format_message(self, msg):
		if msg.server:
			origin = "{}/{}".format(msg.server.name, msg.channel.name)
		else:
			origin = "<private>"
		return "{color}{origin} {msg.author.name}{attachments}: {content}{reset}".format(
			msg=msg,
			origin=origin,
			color=escapes.FORECOLOUR(escapes.random_colour_256(origin)),
			reset=escapes.UNFORMAT,
			content=(msg.clean_content if msg.type == MessageType.default else msg.system_content),
			attachments=(
				"({} attachments)".format(len(msg.attachments))
				if msg.attachments else ""
			),
		)


	def input_loop(self):
		try:
			while True:
				line = self.editor.readline()
				logging.info("read input: {!r}".format(line))
				if not line:
					continue
				# TODO handle commands
		except EOFError:
			logging.info("Got EOF")
		finally:
			logging.info("Closing connection")
			aiogevent.yield_future(self.client.close())


def main(token, log='WARNING', config='~/.ekimdiscord.json'):
	logging.getLogger().setLevel(log)
	config = os.path.expanduser(config)

	# set up asyncio event loop
	asyncio.set_event_loop_policy(aiogevent.EventLoopPolicy())

	EkimDiscord(config, token).run()
