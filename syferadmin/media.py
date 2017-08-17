# Various helper classes to render different kinds of media
import re

from django.conf import settings

from syferadmin.models import Image as SyferImage, Video as SyferVideo


class Media(object):

	def __init__(self, url=None, title=None):
		self.url = url
		self.title = title

	@staticmethod
	def create(url, title=None):
		# Find out what kind of Media this is
		for type in [Image, Video]:
			if type.test.search(url):
				item = type(url, title)
				return item


class Image(Media):
	test = re.compile(r'\.(jpg|jpeg|png|gif)$')

	def __init__(self, url=None, title=None):
		"""Try to find the image locally to support imagespecs"""
		super(Image, self).__init__(url, title)
		try:
			# Also replace "/media/" in url when using a CDN
			urls = [url.replace(settings.MEDIA_URL, ''), url.replace('/media/', '')]
			image = SyferImage.objects.filter(image__in=urls).first()
			self.image = image
		except SyferImage.DoesNotExist:
			self.image = None

	def render(self, **kwargs):
		url = self.url
		if self.image and kwargs:
			url = self.image.resized(**kwargs).url
		return '<img src="{0}" alt="{1}" />'.format(url, self.title)

	def thumb(self):
		return self.render(id='sidepost:post.grid_thumb')


class Video(Media):
	test = re.compile(r'(youtu\.be|youtube\.com|vimeo\.com)')
	thumb_url = None

	def __init__(self, url=None, title=None):
		super(Video, self).__init__(url, title)
		self.video = SyferVideo()
		self.video.info(self.url)

	def render(self, **kwargs):
		return '<div class="video">{}</div>'.format(self.video.render())

	def thumb(self):
		return u'<img src="{0}" alt="{1}" />'.format(self.video.thumb, self.video.name)
