

class ApiError(Exception):
	pass


class HttpClientError(Exception):
	def __init__(self, message, response=None):
		super(HttpClientError, self).__init__(message)
		self.response = response


class HttpServerError(Exception):
	def __init__(self, message, response=None):
		super(HttpServerError, self).__init__(message)
		self.response = response


class ImproperlyConfigured(Exception):
	pass
