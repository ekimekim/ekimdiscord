from setuptools import setup, find_packages

setup(
	name='ekimdiscord',
	version='0.0.1',
	author='Mike Lang',
	author_email='mikelang3000@gmail.com',
	description='terminal client for discord with multiplexing',
	packages=find_packages(),
	install_requires=[
		'aiogevent', # https://github.com/2mf/aiogevent
		'argh',
		'discord.py',
		'gevent',
	],
)
