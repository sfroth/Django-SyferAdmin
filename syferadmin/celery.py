import uuid

from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class MockTask(object):
	def __init__(self, func):
		self.func = func

	def __call__(self, *args, **kwargs):
		return self.func(*args, **kwargs)

	def __str__(self):
		return self.func.__name__

	def __repr__(self):
		return self.__name__

	def apply_async(self, *args, **kwargs):
		return self.delay(*args, **kwargs)

	def delay(self, *args, **kwargs):
		return MockAsyncResult(self.func(*args, **kwargs), self.func)


@python_2_unicode_compatible
class MockAsyncResult(object):
	def __init__(self, results, func):
		self.results = results
		self.name = func.__name__
		self.id = str(uuid.uuid4())

	def __str__(self):
		return self.id

	def __repr__(self):
		return self.id

	def failed(self):
		return False

	def get(self, **useless_options):
		return self.results

	def info(self):
		return self.get()

	def ready(self):
		return True

	@property
	def result(self):
		return self.get()

	def state(self):
		return 'SUCCESS'

	def status(self):
		return 'SUCCESS'

	def successful(self):
		return True


def shared_task(func=None, **useless_options):
	if func is None:
		return shared_task
	else:
		return MockTask(func)
