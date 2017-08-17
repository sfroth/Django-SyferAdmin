from django_jinja import library
from jinja2 import Markup

from syferadmin import json as json_lib


@library.filter
def json(value):
	"""
	Convert a value to the appropriate json representation
	"""
	return Markup(json_lib.dumps(value))
