
import json


class Config(dict):
	"""An editable, persistent config store.
	The contents are stored as JSON in the given filepath.
	Read access is done by simply accessing items:
		foo = config['foo']
	Write access is done by setting attributes, or by mutating the returned values,
	followed by calling save():
		foo = config['foo']
		foo['bar'] = 'abc'
		config['baz'] = 123
		config.save()
	For convenience, this is available as a context manager. It will not save on error:
		with config:
			config['foo'].append('bar')
	You can also re-load from file using load(), but beware this may cause changes to be lost.
	"""

	def __init__(self, filepath):
		self.filepath = filepath
		self.load()

	def load(self):
		with open(self.filepath) as f:
			data = json.load(f)
		self.clear()
		self.update(data)

	def save(self):
		# write-then-rename for atomic overwrite
		temppath = '{}.tmp'.format(self.filepath)
		with open(temppath, 'w') as f:
			json.dump(self, f)
		os.rename(tempfile, self.filepath)

	def __enter__(self):
		return self

	def __exit__(self, *exc_info):
		if exc_info == (None, None, None):
			self.save()
