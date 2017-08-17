from django.core import exceptions, validators


class RelativeURLValidator(validators.URLValidator):
	def __call__(self, value):
		try:
			super().__call__(value)
		except exceptions.ValidationError:
			if value.startswith('/'):
				newvalue = 'https://www.example.com{}'.format(value)
				super().__call__(newvalue)
				return value
			raise
