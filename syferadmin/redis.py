import socket

from django_redis.client import DefaultClient
from django_redis.exceptions import ConnectionInterrupted

from redis.exceptions import ConnectionError
from redis.exceptions import ResponseError

# Compatibility with redis-py 2.10.x+

try:
	from redis.exceptions import TimeoutError
	_main_exceptions = (TimeoutError, ResponseError, ConnectionError, socket.timeout)
except ImportError:
	_main_exceptions = (ConnectionError, socket.timeout)


class SyferadminRedisClient(DefaultClient):
	"""
	Override the default django_redis client as iter_keys is
	very slow when updating small subsets frequently
	"""

	def delete_pattern(self, pattern, version=None, prefix=None, client=None):
		"""
		Remove all keys matching pattern.
		"""

		if client is None:
			client = self.get_client(write=True)

		pattern = self.make_key(pattern, version=version, prefix=prefix)
		try:
			keys = client.keys(pattern)

			if keys:
				return client.delete(*keys)
		except _main_exceptions as e:
			raise ConnectionInterrupted(connection=client, parent=e)

	def delete_pattern_iter(self, *args, **kwargs):
		"""
		Fallback to original delete_pattern method
		"""
		return super().delete_pattern(*args, **kwargs)
