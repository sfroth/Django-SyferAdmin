import requests

from django.core.cache import cache


class Social(object):
	"""
	Social Network Helper
	"""
	networks = {
		'Facebook': {
			'sort': 0,
			'url': 'http://facebook.com/{0}',
			'handle': '{0}',
		},
		'Instagram': {
			'sort': 1,
			'url': 'http://instagram.com/{0}',
			'api': 'http://instagram.sidestudios.com/json.php',
			'handle': '@{0}',
		},
		'Google Plus': {
			'sort': 2,
			'url': 'http://plus.google.com/{0}',
			'handle': '+{0}',
		},
		'Pinterest': {
			'sort': 3,
			'url': 'http://pinterest.com/{0}/',
			'handle': '{0}',
		},
		'Twitter': {
			'sort': 4,
			'url': 'http://twitter.com/{0}',
			'handle': '@{0}',
		},
		'Tumblr': {
			'sort': 5,
			'url': 'http://{0}.tumblr.com/',
			'handle': '{0}',
		},
		'Vimeo': {
			'sort': 6,
			'url': 'http://vimeo.com/{0}',
			'handle': '{0}',
		},
		'Youtube': {
			'sort': 7,
			'url': 'http://youtube.com/user/{0}',
			'handle': '{0}',
		},
		'LinkedIn': {
			'sort': 8,
			'url': 'http://www.linkedin.com/in/{0}',
			'handle': '{0}',
		},
	}

	@classmethod
	def url(cls, network, account):
		return cls.networks[network]['url'].format(account)

	@classmethod
	def handle(cls, network, account):
		return cls.networks[network]['handle'].format(account)


class Instagram(Social):
	"""
	Instagram Helper
	"""
	def __init__(self, *args, **kwargs):
		self.network = self.networks[self.__class__.__name__]

	def images(self, username=None, tag=None, count=1):
		cache_key = "instagram-{}-{}-{}".format(username, tag, count)
		images = cache.get(cache_key)
		if images:
			return images

		args = {'count': count}
		if username:
			args['username'] = username
		if tag:
			args['tag'] = tag

		try:
			data = requests.get(self.network['api'], params=args, timeout=2).json()
			if data['images']['data']:
				for key in range(len(data['images']['data'])):
					for imagetype, image in data['images']['data'][key]['images'].items():
						data['images']['data'][key]['images'][imagetype]['url'] = image['url'].replace('http://', 'https://')

				cache.set(cache_key, data['images']['data'], 1800)
				return data['images']['data']
		except Exception:
			pass
		return None

	def url(self, account):
		return super(Instagram, self.__class__.__name__, account)
