from django_jinja import library
import hashlib


@library.filter
def hash(value, algo='md5'):
	"""
	Hashes a string using algo
	"""
	h = hashlib.new(algo)
	h.update(value.encode('utf-8'))
	return h.hexdigest()
