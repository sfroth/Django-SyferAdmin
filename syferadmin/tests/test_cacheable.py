import random
import string

from django.test import TestCase
from django.core import cache
from mock import patch

from syferadmin import decorators
from syferadmin.decorators import cacheable


def generate_random():
	return "".join(random.choice(string.ascii_uppercase) for i in range(10))


class FakeModel:
	pk = 1

	def fake_func(self):
		return generate_random()

	@cacheable
	def fake_func_a(self):
		return generate_random()

	@cacheable
	def fake_func_b(self, *args, **kwargs):
		return generate_random()


def fake_func():
	return generate_random()


@cacheable
def fake_func_a():
	return generate_random()


@cacheable
def fake_func_none():
	return None


class CacheableTestCase(TestCase):
	fixtures = ['syferadmin/tests/fixtures/region.json']

	def setUp(self):
		# Set test model instance
		self.model = FakeModel()
		# Set local memory cache
		self.locmem_cache = cache.get_cache('django.core.cache.backends.locmem.LocMemCache')
		self.locmem_cache.clear()
		self.patch = patch.object(decorators, 'cache', self.locmem_cache)
		self.patch.start()

	def tearDown(self):
		"Kill caches"
		self.patch.stop()

	def test_class_instance(self):
		a1 = self.model.fake_func()
		a2 = self.model.fake_func()
		self.assertNotEqual(a1, a2)
		a1 = self.model.fake_func_a()
		a2 = self.model.fake_func_a()
		self.assertEqual(a1, a2)

	def test_simple_function(self):
		a1 = fake_func()
		a2 = fake_func()
		self.assertNotEqual(a1, a2)
		a1 = fake_func_a()
		a2 = fake_func_a()
		self.assertEqual(a1, a2)

	def test_uncache(self):
		a1 = fake_func_a()
		a2 = fake_func_a()
		self.assertEqual(a1, a2)
		a2 = fake_func_a(uncache=True)
		self.assertNotEqual(a1, a2)

	def test_with_args(self):
		b1 = self.model.fake_func_b()
		b2 = self.model.fake_func_b(test_arg=1)
		self.assertNotEquals(b1, b2)
		b1 = self.model.fake_func_b(test_arg=2)
		b2 = self.model.fake_func_b(test_arg=2)
		self.assertEqual(b1, b2)

	def test_is_none(self):
		none = fake_func_none()
		self.assertIsNone(none)
		none = fake_func_none()
		self.assertIsNone(none)
