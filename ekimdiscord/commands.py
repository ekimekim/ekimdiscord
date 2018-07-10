
import logging

from classtricks import classproperty, get_all_subclasses


def filter_prefix(prefix, items):
	"""Helper for autocomplete, returns all items which begin with prefix."""
	return [item for item in items if item.startswith(prefix)]


def as_dict(items, key='name', lower=True):
	return {getattr(item, key).lower(): item for item in items}


class Command(object):
	"""
	Commands register themselves by inheriting from this class.
	Commands must define the following:
		name: Leading word (no spaces) used to invoke command.
		      Defaults to class __name__.lower()
		parse(text): Takes text following the command name and parses it into
		             something to pass to run(). In addition, returns info for
		             auto-complete. Return value should be (kwargs for run, fixed completion prefix, list of completions),
		             substituting a string error message for kwargs on parse error.
		run(**kwargs_from_parse): Actually run the command.
	The parent EkimDiscord class is available as self.parent.
	As a convenience, self.write() is available as a shortcut to self.parent.editor.write()
	"""

	# By directly specifying abstract = True in class's __dict__, marks it to not be considered
	# an actual command.
	abstract = True

	@classmethod
	def get_commands(cls):
		"""Return all command classes in a map {name: cls}"""
		return {
			subcls.name: subcls
			for subcls in get_all_subclasses(cls)
			if not subcls.__dict__.get('abstract')
		}

	def __init__(self, parent):
		self.parent = parent
		self.write = self.parent.editor.write

	def _run(self, text):
		kwargs, _, _ = self._parse(text)
		if not isinstance(kwargs, dict):
			self.write("{}: bad command: {}".format(self.name, kwargs))
			return
		try:
			self.run(**kwargs)
		except Exception:
			logging.exception("Got error trying to run command {!r} with args {!r}".format(self.name, kwargs))

	def _parse(self, text):
		try:
			kwargs, prefix, completions = self.parse(text)
		except Exception as e:
			logging.exception("Got error trying to parse text for command {!r}: {!r}".format(self.name, text))
			return "{}: {}".format(type(e).__name__, e), '', []
		return kwargs, prefix, completions

	def _complete(self, text):
		_, prefix, completions = self._parse(text)
		return prefix, completions

	@classproperty
	def name(cls):
		return cls.__name__.lower()

	def parse(self, text):
		return "parse not implemented", []

	def run(self, **kwargs):
		raise NotImplementedError


class ChannelCommand(Command):
	"""Common parsing code for commands which target a particular server/channel.
	Commands look like this:
		NAME SERVER/CHANNEL [EXTRA ARGS]
	parse() will set kwargs 'server', 'channel' and 'extra'. It is suggested subclasses
	override parse(), call super(), then do further processing on 'extra'.
	Note that extra will be None if there is no trailing space after channel, and '' if there is,
	ie. extra = None indicates the channel may still be partially typed.
	"""

	abstract = True

	def parse(self, text):
		servers = as_dict(self.parent.client.servers)
		if '/' not in text:
			# we're still typing server name
			return "no channel given", '', filter_prefix(text.lower(), servers)
		server, remaining = text.split('/', 1)
		prefix = ''
		complete = []
		if ' ' in remaining:
			channel, extra = remaining.split(' ', 1)
		else:
			channel, extra = remaining, None
			if server.lower() in servers:
				prefix = '{}/'.format(server)
				complete = filter_prefix(channel.lower(), as_dict(servers[server.lower()].channels))
		return {
			'server': server.lower(),
			'channel': channel.lower(),
			'extra': extra,
		}, prefix, complete


class Ignore(ChannelCommand):
	"""Ignore a channel, suppressing further messages (unless they mention me) from being displayed."""
	def run(self, server, channel, extra=None):
		servers = as_dict(self.parent.client.servers)
		if server not in servers:
			self.write("No such server: {!r}".format(server))
			return
		channels = as_dict(servers[server].channels)
		if channel not in channels:
			self.write("No such channel: {!r}".format(channel))
			return
		with self.parent.config as config:
			ignore_list = config.setdefault('ignore', [])
			if (server, channel) not in ignore_list:
				ignore_list.append([server, channel])
		self.write("Ignored channel {}/{}".format(server, channel))
