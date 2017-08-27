# coding=utf-8
from __future__ import unicode_literals

import base64
import os
import pickle
import pytz
import re
import requests

from django.conf import settings
from django.core import validators
from django.core.cache import cache
from django.core.files import File
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from imagekit.cachefiles import ImageCacheFile
from jsonfield import JSONField

from .decorators import cacheable
from .fields import ImageUploaderField, model_fields
from .imagespecs import *
from .managers import RegionManager, SettingQueryset, UserManager
from .mixins import AlignmentMixin, ImageContainer, ImageResizable, MetaModel, RegionalModel, RelatableModel, SchedulableModel, SortableModel, StyleMixin, TextAlignmentMixin, TrackableModel
from .social import Instagram
from .uploader.helpers import UploadThumbSpec
from .utils import generate_image_path, human_join, MockImage


@python_2_unicode_compatible
class Image(ImageResizable, TrackableModel, SortableModel):
	content_type = models.ForeignKey(ContentType)
	object_id = models.PositiveIntegerField(null=True, db_index=True)
	content_object = GenericForeignKey('content_type', 'object_id')
	name = models.CharField(max_length=100, null=True, blank=True)
	description = models.TextField(blank=True)
	image = ImageUploaderField(upload_to=generate_image_path, max_length=255)
	group = models.CharField(max_length=25, null=True, blank=True)

	class Meta(SortableModel.Meta):
		index_together = [
			['object_id', 'content_type'],
		]

	def __str__(self):
		return str(self.image)

	@property
	def image_path(self):
		path = self.content_object.image_path
		if self.name:
			path += '-' + self.name
		return path

	def render(self):
		"Render within Uploader context"
		thumb = ImageCacheFile(UploadThumbSpec(source=self.image))
		try:
			return '<img src="{}" />'.format(thumb.url)
		except IOError:
			return "Source not found"

	@property
	def url(self):
		return settings.MEDIA_URL + self.image.name


class Video(ImageResizable, TrackableModel, SortableModel):
	VIDEO_TYPES = {
		'youtube': {
			'regex': r'^.*(?:(?:youtu.be\/)|(?:v\/)|(?:\/u\/\w\/)|(?:embed\/)|(?:watch\?))\??v?=?(?P<key>[^#\&\?\"]*).*?(?:&list=(?P<list>[^#\&\?\"]+))?.*?(?:#t=(?P<start_time>\d+))?',
			'api': 'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={key}&key=AIzaSyAYj2M-Pomtkw4eUUSqYaqmzs1phftbCv4',
			'url': 'https://www.youtube.com/watch?v={key}&rel=0',
			'iframe_url': 'https://www.youtube.com/embed/{key}' +
				'?rel=0&iv_load_policy=3&hd=1&autohide=1&showinfo=0&start={start}' +
				'&list={list}&listType=playlist',
		},
		'vimeo': {
			'regex': r'^.*vimeo.com\/(?:video\/)?(?P<key>\d+).*',
			'api': 'https://vimeo.com/api/v2/video/{key}.json',
			'url': 'https://www.vimeo.com/{key}',
			'iframe_url': 'https://player.vimeo.com/video/{key}?title=0&byline=0&portrait=0',
		},
	}
	content_type = models.ForeignKey(ContentType)
	object_id = models.PositiveIntegerField(null=True)
	content_object = GenericForeignKey('content_type', 'object_id')
	name = models.CharField(max_length=250, null=True, blank=True)
	description = models.TextField(blank=True)
	type = models.CharField(max_length=50)
	key = models.CharField(max_length=50)
	thumb = models.CharField(max_length=250, null=True, blank=True)
	width = models.SmallIntegerField(null=True, blank=True)
	height = models.SmallIntegerField(null=True, blank=True)

	class Meta(SortableModel.Meta):
		pass

	def __init__(self, *args, **kwargs):
		self.start_time = 0
		self.list = None
		super(Video, self).__init__(*args, **kwargs)

	def parse(self, url):
		"""Loop through video type regexes and try to parse
		this video URL.

		Sets attributes on itself based on regex keys.
		"""
		for video_type in self.VIDEO_TYPES:
			try:
				match = re.compile(self.VIDEO_TYPES[video_type]['regex']).search(url)
			except KeyError:
				continue
			if not match:
				continue
			self.type = video_type
			for attr, value in match.groupdict().items():
				if value is not None:
					setattr(self, attr, value)

	def url(self, url_type='url'):
		info = {'key': self.key, 'start': self.start_time, 'list': self.list}
		url = self.VIDEO_TYPES[self.type][url_type].format(**info)
		# Turn on showinfo if part of a playlist
		if self.list:
			url = url.replace('showinfo=0', 'showinfo=1')
		return url

	def get_api(self, force=False):
		"Get api response for video key"
		cache_key = 'video-api-{}'.format(self.key)
		result = cache.get(cache_key)
		if force or not result:
			result = requests.get(self.url('api'), timeout=10).json()
			cache.set(cache_key, result, (5 * 60))
		return result

	@property
	def image_path(self):
		return 'videos/{}-{}'.format(self.type, self.key)

	def info(self, video_url=None):
		if video_url:
			self.parse(video_url)
		try:
			data = self.get_api()
		except Exception:
			self.width = 0
			self.height = 0
		else:
			self.width = 0
			self.height = 0
			try:
				if data and self.type == 'youtube':
					data = data['items'][0]['snippet']
					thumbnails = data.get('thumbnails', {})
					for quality in ('maxres', 'standard', 'high', 'medium', 'default'):
						if quality in thumbnails:
							thumb = thumbnails.get(quality, {})
							self.thumb = thumb.get('url')
							self.width = thumb.get('width', 0)
							self.height = thumb.get('height', 0)
							break

					self.name = data.get('title')
					self.description = data.get('description')

				if data and self.type == 'vimeo':
					data = data[0]
					self.name = data.get('title')
					self.description = data.get('description')
					self.thumb = data.get('thumbnail_large')
					self.width = data.get('width', 0)
					self.height = data.get('height', 0)
			except (IndexError, KeyError):
				pass
			return data

	def render(self):
		return '<iframe src="{}" frameborder="0" allowfullscreen></iframe>'.format(self.url('iframe_url'))

	def resized(self, source='image', id='imagekit:thumbnail', dest=None, **kwargs):
		if not self.thumb:
			return
		ext = os.path.splitext(self.thumb)[1].lower()[1:]
		file_path = '{}/{}.{}'.format(settings.MEDIA_ROOT, self.image_path, ext)
		self.image = None

		try:
			# Line is repeated to emulate Django's ImageFieldFile
			self.image = File(open(file_path, 'rb'))
			self.image.file = File(open(file_path, 'rb'))
		except IOError:
			# Get image local
			try:
				request = requests.get(self.thumb, stream=True, timeout=3)
			except requests.exceptions.RequestException:
				pass
			else:
				if request.status_code == requests.codes.ok:
					directory = os.path.join(settings.MEDIA_ROOT, 'videos')
					if not os.path.exists(directory):
						os.makedirs(directory)

					img = open(file_path, 'w+b')
					img.write(request.content)
					img.close()
					# Line is repeated to emulate Django's ImageFieldFile
					self.image = File(open(file_path, 'rb'))
					self.image.file = File(open(file_path, 'rb'))

		if self.image:
			return super(Video, self).resized(source, id, dest, **kwargs)


@python_2_unicode_compatible
class Region(SortableModel):
	TIMEZONES = [(tz, tz) for tz in pytz.common_timezones]
	name = models.CharField(max_length=50)
	slug = models.SlugField(unique=True)
	timezone = models.CharField(max_length=50, choices=TIMEZONES, default='America/Los_Angeles')
	locale = models.CharField(max_length=10, null=True, blank=True)
	parent = models.ForeignKey('self', null=True, blank=True)
	admin = models.BooleanField(default=True)
	objects = RegionManager()

	def __str__(self):
		return self.name

	def admin_name(self):
		name = self.name
		if self.children():
			name = '{} ({})'.format(name, self.children_list())
		return name

	def allows(self, perms):
		if not isinstance(perms, (list, tuple)):
			perms = (perms,)
		for perm in perms:
			if perm == 'shopping' and not self.warehouse:
				return False
		return True

	def children(self):
		return Region.objects.children(self)

	def children_list(self):
		return human_join([a.name for a in self.children()])

	def verify_unique_by_region(self, cleaned_data, obj):
		"""
		Replaces the m2m_changed receiver for validating model uniqueness in a region
		"""
		if self:
			for field in ('url_path', 'slug'):
				# cleaned_data will be None if checking from a region toggle from the change list view
				if cleaned_data:
					filters = {field: cleaned_data.get(field, None)}
				else:
					filters = {field: getattr(obj, field, None)}
				if hasattr(obj, field) and obj.__class__.objects.exclude(pk=obj.pk).filter(**filters).filter(regions=self):
					return False
		return True

	@property
	def tzinfo(self):
		return pytz.timezone(self.timezone)


class RegionCountry(models.Model):
	region = models.ForeignKey(Region, related_name='countries')
	country_code = models.CharField(max_length=2)


@python_2_unicode_compatible
class Related(SortableModel):
	"""
	Relates any one entry to another entry of any content type
	"""
	content_type = models.ForeignKey(ContentType)
	object_id = models.PositiveIntegerField(db_index=True)
	content_object = GenericForeignKey('content_type', 'object_id')
	group = models.CharField(max_length=100)
	vars = JSONField(null=True, blank=True)

	related_content_type = models.ForeignKey(ContentType, related_name="related_link")
	related_object_id = models.PositiveIntegerField(db_index=True)
	related_content_object = GenericForeignKey('related_content_type', 'related_object_id')

	class Meta(SortableModel.Meta):
		ordering = ['related_content_type__model', 'group', 'sort', ]
		verbose_name = 'related item'
		verbose_name_plural = 'related items'

	def __str__(self):
		return '{0}: {1}'.format(self.content_type.name, self.content_object)


@python_2_unicode_compatible
class Setting(TrackableModel):
	key = models.CharField(max_length=100)
	value = models.TextField()
	region = models.ForeignKey('Region', default=None, blank=True, null=True)
	defaults = {
		'admin': False,
		'default': None,
		'description': None,
		'name': None,
		'options': [],
		'placeholder': None,
		'type': 'text',
	}
	objects = SettingQueryset.as_manager()

	class Meta:
		unique_together = (('key', 'region'),)

	def __init__(self, *args, **kwargs):
		for attribute, default in self.defaults.items():
			setattr(self, attribute, kwargs.pop(attribute, default))
		super(Setting, self).__init__(*args, **kwargs)

	def __str__(self):
		return self.key

	def decode(self):
		if self.type == 'credentials':
			return pickle.loads(base64.b64decode(self.value), encoding="bytes")
		raise TypeError('No decoder for type {}!'.format(self.type))

	def get_name(self):
		if self.name:
			return self.name
		return self.key.split('.')[-1].replace('_', ' ').title()

	def get_value(self):
		if self.value is None:
			if getattr(self, 'region_id', None):
				try:
					return Setting.objects.get(key=self.key, region=None).get_value()
				except Setting.DoesNotExist:
					pass
			return self.default
		if self.type == 'bool':
			return False if self.value in ["False", "false", ""] else True
		if self.type == 'select_multiple':
			return self.value.split(',')
		return self.value

	def save(self, *args, **kwargs):
		if self.type == 'credentials':
			self.value = base64.b64encode(pickle.dumps(self.value))
		elif type(self.value) is list:
			self.value = ','.join(self.value)
		return super(Setting, self).save(*args, **kwargs)


class User(AbstractBaseUser, RegionalModel, TrackableModel, PermissionsMixin, MetaModel):
	name = models.CharField(_('name'), max_length=60, blank=True)
	username = models.CharField(_('username'), max_length=50, validators=[validators.RegexValidator(re.compile(settings.SYFERADMIN_USER_USERNAME_REGEX), _('Enter a valid username.'), 'invalid')], blank=True)
	email = models.EmailField(_('email address'), unique=True)
	is_staff = models.BooleanField(_('staff status'), default=False,
		help_text=_('Designates whether the user can log into this admin site.'))
	is_active = models.BooleanField(_('active'), default=True,
		help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
	USERNAME_FIELD = 'email'
	objects = UserManager()

	class Meta:
		verbose_name = 'Staff Member'

	@property
	def first_name(self):
		if not self.name:
			return "Anonymous"
		return self.name.split(None, 1)[0]

	@classmethod
	def foreignkey_search(cls, request, term):
		return User.objects.filter(models.Q(name__icontains=term) | models.Q(email__icontains=term))

	def foreignkey_search_formatter(self):
		return '<div><strong>{}</strong> <small style="display: block;color: #333;">{}</small></div>'.format(self.name, self.email)

	def get_full_name(self):
		return self.name

	def get_short_name(self):
		return self.first_name

	def gravatar(self, size=20):
		"Return user gravatar"
		import hashlib
		return "https://secure.gravatar.com/avatar/{}?s={}&amp;d=mm".format([hashlib.md5(self.email.strip().lower()).hexdigest(), size])

	def greeting(self):
		from random import choice
		# Set greetings
		greetings = ['Welcome, {}']
		return choice(greetings).format(self.first_name)

	@cached_property
	def groups_list(self):
		return list(self.groups.values_list('pk', flat=True))

	@property
	def has_all_regions(self):
		return Region.objects.parents() == self.regions.parents()

	@property
	def last_name(self):
		if len(self.name.split(' ')) == 1:
			return None
		return ' '.join(self.name.split(' ')[1:])

	def name_or_email(self):
		return self.name or self.email

	def note(self, message, user=None, key=None):
		"""Add a note to this order

		:param message: Note message
		:param user: User adding the message (None for system)
		:param key: Key to group this note under (for fishing out specific notes later)
		"""
		self.notes.create(content=message, key=key, user=user)


class UserLogin(RegionalModel, TrackableModel):
	user = models.ForeignKey('User')
	region = models.ForeignKey('Region', default=None, blank=True, null=True)
	successful = models.BooleanField(default=False)
	ip_address = models.GenericIPAddressField()
	user_agent = models.TextField()

	class Meta:
		ordering = ['-created']

	@classmethod
	def create(cls, **kwargs):
		kwargs['ip_address'] = '127.0.0.1'
		if 'request' in kwargs:
			request = kwargs.pop('request')
			kwargs['ip_address'] = request.META.get('REMOTE_ADDR', '127.0.0.1')
			kwargs['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
			if hasattr(request, 'region'):
				kwargs['region'] = request.region
		return cls(**kwargs)

	@property
	def browser(self):
		ua = self.user_agent.lower()
		if 'firefox' in ua:
			return 'firefox'
		if 'msie' in ua or 'trident' in ua or 'edge/' in ua:
			return 'ie'
		if 'opera' in ua:
			return 'opera'
		if 'chrome' in ua or 'crios' in ua:
			return 'chrome'
		if 'safari' in ua:
			return 'safari'

	@property
	def os(self):
		ua = self.user_agent.lower()
		if 'os x' in ua:
			return 'osx'
		if 'windows' in ua:
			return 'windows'
		if 'android' in ua:
			return 'android'
		if 'linux' in ua:
			return 'linux'


@python_2_unicode_compatible
class Meta(TrackableModel):
	"General Meta Model to add additional data to any content type"
	object_id = models.PositiveIntegerField(null=True)
	content_type = models.ForeignKey(ContentType)
	content_object = GenericForeignKey('content_type', 'object_id')
	key = models.CharField(max_length=100)
	value = models.CharField(max_length=3072)

	class Meta:
		unique_together = (("object_id", "content_type", "key"),)

	def __str__(self):
		return "{0}: {1}".format(self.key, self.value)

	def languages():
		return getattr(settings, 'LANGUAGES', None)


@python_2_unicode_compatible
class UserNote(TrackableModel):
	noted_user = models.ForeignKey('syferadmin.User', related_name='notes')
	user = models.ForeignKey('syferadmin.User', null=True, related_name='+')
	key = models.CharField(max_length=50, null=True)
	content = models.TextField()

	class Meta:
		ordering = ('-created', '-pk')

	@staticmethod
	def types():
		return settings.SYFERADMIN_USER_NOTE_TYPES or ()

	def __str__(self):
		note = self.content
		if self.key and self.key in dict(self.types()):
			note = '({}) {}'.format(dict(self.types())[self.key], note)
		return note
