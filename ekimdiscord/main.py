
import asyncio
import logging

import aiogevent
import discord
import gevent.pool
from discord.enums import MessageType

import escapes
import lineedit


LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"


def format_message(msg):
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


def main(token, log='INFO'):
	logging.getLogger().setLevel(log)

	group = gevent.pool.Group()

	# set up asyncio event loop
	asyncio.set_event_loop_policy(aiogevent.EventLoopPolicy())
	loop = asyncio.get_event_loop()

	client = discord.Client()
	editor = lineedit.LineEditing(input_fn=lineedit.gevent_read_fn, gevent_handle_sigint=True)
	editor_log_handler = lineedit.LoggingHandler(editor)
	editor_log_handler.setFormatter(logging.Formatter(LOG_FORMAT))

	@client.event
	async def on_message(message):
		return await aiogevent.wrap_greenlet(group.spawn(_on_message, message))
	def _on_message(message):
		editor.write(format_message(message))

	@group.spawn
	def input_loop():
		try:
			while True:
				line = editor.readline()
				logging.info("read input: {!r}".format(line))
				if not line:
					continue
				# TODO handle commands
		except EOFError:
			logging.info("Got EOF")
		finally:
			logging.info("Closing connection")
			aiogevent.yield_future(client.close())

	with editor, editor_log_handler:
		# blocks until client quit
		loop.run_until_complete(client.start(token, bot=False))
