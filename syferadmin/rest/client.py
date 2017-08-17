import requests

from .. import json
from .exceptions import HttpClientError, HttpServerError, ImproperlyConfigured


class RestClient(object):
	"""
	Basic rest client helper built on requests
	Usage:
		# get
		RestClient('http://example.com/api/').get('cats', id=1)  # {'data': {'name': 'Mr. Mistoffelees'}}

		# post
		RestClient('http://example.com/api/').post('cats/add', {'name': 'Panthro'})  # {'status': 'success'}
	"""
	base_url = None
	content_type = 'application/json'
	headers = {
		'Accept': content_type,
		'Content-Type': content_type,
	}
	proxies = None
	timeout = None
	verify = True

	METHODS = ['get', 'options', 'head', 'post', 'put', 'patch', 'delete']

	def __getattr__(self, method):
		"""
		Returns wrapper method for request from available methods
		"""
		if method not in self.METHODS:
			raise AttributeError(method)

		def wrapper(url, data=None, **kwargs):
			process_response = kwargs.pop('process_response', True)
			resp = self.request(method.upper(), url=url, data=data, params=kwargs)
			return self.response(resp) if process_response else resp

		return wrapper

	def __init__(self, base_url=None, session=None):
		if base_url:
			self.base_url = base_url

		if not self.base_url:
			raise ImproperlyConfigured('Api url is required')

		self.session = session or requests.session()

	def request(self, method, url, data=None, params=None):
		"""
		Build request
		"""
		url = '{}/{}'.format(self.base_url.rstrip('/'), url.lstrip('/'))
		data = json.dumps(data)
		resp = self.session.request(method, url, data=data, params=params, headers=self.headers, proxies=self.proxies, timeout=self.timeout, verify=self.verify)

		if 400 <= resp.status_code <= 499:
			raise HttpClientError('Client Error {}'.format(resp.status_code), resp)
		elif 500 <= resp.status_code <= 599:
			raise HttpServerError('Server Error {}'.format(resp.status_code), resp)

		return resp

	def response(self, response):
		return response.json()
