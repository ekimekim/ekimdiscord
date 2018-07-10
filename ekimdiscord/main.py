
import asyncio
import logging
import random
import os

import aiogevent
import discord
import gevent.pool
from discord.enums import MessageType

import escapes
import lineedit

from .config import Config
from .commands import Command

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"


class EkimDiscord(object):

	def __init__(self, configpath, token):
		self.group = gevent.pool.Group()
		self.config = Config(configpath)
		self.token = token
		self.editor = lineedit.LineEditing(
			input_fn=lineedit.gevent_read_fn, gevent_handle_sigint=True,
			completion=self.complete, complete_whole_line=True,
		)
		self.client = discord.Client()
		# randomise color allocations on each startup
		self.color_seed = random.random()

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


	def on_message(self, msg):
		if (
			msg.server and
			[msg.server.name.lower(), msg.channel.name.lower()] in self.config.get('ignore', [])
		):
			return
		self.editor.write(self.format_message(msg))


	def format_message(self, msg):
		if msg.server:
			origin = "{}/{}".format(msg.server.name, msg.channel.name)
		else:
			origin = "<private>"
		return "{color}{origin} {msg.author.name}{attachments}: {content}{reset}".format(
			msg=msg,
			origin=origin,
			color=escapes.FORECOLOUR(escapes.random_colour_256((self.color_seed, origin))),
			reset=escapes.UNFORMAT,
			content=(msg.clean_content if msg.type == MessageType.default else msg.system_content),
			attachments=(
				"({} attachments)".format(len(msg.attachments))
				if msg.attachments else ""
			),
		)


	def complete(self, text):
		commands = Command.get_commands()
		if ' ' not in text:
			# auto-complete to a command
			return '', [command for command in commands if command.startswith(text)]
		# pass to command to determine completions, if any
		command, text = text.split(' ', 1)
		if command in commands:
			prefix, completions = commands[command](self)._complete(text)
			prefix = '{} {}'.format(command, prefix)
			return prefix, completions
		return '', []


	def input_loop(self):
		try:
			while True:
				line = self.editor.readline()
				logging.info("read input: {!r}".format(line))
				if not line:
					continue
				if ' ' in line:
					command, text = line.split(' ', 1)
				else:
					command, text = line, ''
				commands = Command.get_commands()
				if command not in commands:
					self.editor.write("Unknown command: {!r}".format(command))
					continue
				commands[command](self)._run(text)
		except EOFError:
			logging.info("Got EOF")
		except Exception:
			logging.critical("Fatal error in input loop", exc_info=True)
		finally:
			logging.info("Closing connection")
			aiogevent.yield_future(self.client.close())


def main(token, log='WARNING', config='~/.ekimdiscord.json'):
	logging.getLogger().setLevel(log)
	config = os.path.expanduser(config)

	# set up asyncio event loop
	asyncio.set_event_loop_policy(aiogevent.EventLoopPolicy())

	EkimDiscord(config, token).run()
