from __future__ import absolute_import
import sys


class JSON:
	"Override of standard json lib with default cleaning method"

	def __getattr__(self, name):
		import json
		return getattr(json, name)

	def clean(self, obj):
		import decimal
		if isinstance(obj, decimal.Decimal):
			return float(obj)
		import datetime
		if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
			return obj.isoformat()

	def dumps(self, *args, **kwargs):
		import json
		if 'default' not in kwargs:
			kwargs['default'] = self.clean
		return json.dumps(*args, **kwargs)

sys.modules[__name__] = JSON()
