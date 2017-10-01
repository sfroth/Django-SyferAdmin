#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import time
import datetime
from copy import deepcopy
import uuid

from django.apps import apps
from django.core.cache import cache
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.apps import apps
from django.template import Context, Template
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils import formats, timezone
from imagekit import register, unregister
from imagekit.exceptions import AlreadyRegistered, NotRegistered
from imagekit.utils import suggest_extension
from inlinestyler.utils import inline_css
from hashlib import md5

from .middleware.threadlocal import get_request


class DummyCacheLock(object):
	"Dummy cache lock when we don't have access to cache.lock"
	def __init__(self, *args, **kwargs):
		pass

	def __enter__(self):
		pass

	def __exit__(self, *args):
		pass


class MockImage(object):
	'Way to mock an image for django-imagekit formatting'

	def __init__(self, url):
		self.url = url


def absolute_url(url):
	"Convert a relative URL to an absolute URL"
	if not url:
		return
	if url.startswith('//'):
		return ''.join(['https:' if settings.Site.enable_ssl else 'http:', url])
	return ''.join([settings.ROOT_URL, url])


def current_currency():
	from .models import Region
	try:
		return current_region().currency
	except Region.DoesNotExist:
		return None


def current_currency_id():
	currency = current_currency()
	if currency:
		return currency.id


def current_region():
	from .models import Region
	try:
		request = get_request()
		if hasattr(request, 'region'):
			return request.region
		region_id = request.COOKIES.get(settings.SYFERADMIN_REGION_COOKIE_NAME, None)
		return Region.objects.get(pk=region_id)
	except (Region.DoesNotExist, AttributeError):
		try:
			return Region.objects.all()[0]
		except IndexError:
			raise Region.DoesNotExist("No regions found! Please create one before continuing.")


def current_region_id():
	region = current_region()
	if region:
		return region.id


def current_user():
	request = get_request()
	if hasattr(request, 'user'):
		return request.user


def date_display(obj, field, default=None):
	if getattr(obj, field, default):
		return """<span title="{}">{}<br />{}</span>""".format(
			timezone.get_current_timezone_name(),
			formats.date_format(timezone.localtime(getattr(obj, field)), 'SHORT_DATE_FORMAT'),
			formats.date_format(timezone.localtime(getattr(obj, field)), 'TIME_FORMAT')
		)
	return getattr(obj, field, default)


def dict_merge(a, b):
	"""
	Recursively merges dict's. not just simple a['key'] = b['key'], if
	both a and bhave a key who's value is a dict then dict_merge is called
	on both values and the result stored in the returned dictionary.
	"""
	if not isinstance(b, dict):
		return b
	result = deepcopy(a)
	for k, v in b.items():
		if k in result and isinstance(result[k], dict):
				result[k] = dict_merge(result[k], v)
		else:
			result[k] = deepcopy(v)
	return result


def disconnect():
	"Kill the db connection for long running tasks"
	from django.db import connection
	connection.close()


def generate_email(subject, template_path, to_emails, context):
	"""
	Generates a multi-part text/html email from a group of templates,
	and updates the context to include the current Site and subject.

	Automatically sends from the set company name/email in the config,
	and inlines any css in the HTML content.
	"""
	from .settings import Settings

	# Region settings
	region = context.get('region', None)
	settings_ = Settings.load('values', region)
	site = Site.objects.get_current()
	template_split = template_path.split('/')
	template_name = template_split[len(template_split) - 1].split('.')[0]

	context.update({'settings': settings_, 'site': site, 'subject': subject})
	text, html = [render_to_string(template_path.format(mime_type), context) for mime_type in ('text', 'html')]
	html = html.replace('href="/', 'href="http://{}/'.format(site))
	try:
		from_email = '{} <{}>'.format(settings_.Company.name, settings_.Company.email)
	except AttributeError:
		from_email = settings.DEFAULT_FROM_EMAIL
	email = EmailMultiAlternatives(subject, text, from_email, to_emails, headers={'X-MC-Tags': template_name})
	if '<!-- endnoinline -->' in html:
		html = html.replace('<!-- noinline -->', '<!-- noinline$')
	html = inline_css(html)
	html = html.replace('<!-- noinline$', '<!-- noinline -->')
	email.attach_alternative(html, "text/html")
	return email


def generate_file_hash(prefix=''):
	return "{}{}".format(prefix, str(uuid.uuid4())[:4])


def generate_image_path(instance, filename, suffix=''):
	return instance.image_path + suffix + generate_file_hash('-') + os.path.splitext(filename)[1]


def generate_video_path(instance, filename, suffix=''):
	return instance.video_path + suffix + generate_file_hash('-') + os.path.splitext(filename)[1]


def generate_file_path(instance, filename, suffix=''):
	return instance.file_path + suffix + generate_file_hash('-') + os.path.splitext(filename)[1]


def get_model_attr(model_path, attr):
	"""
	Returns a model attribute based on model_path as app_label.model_name
	"""
	model = get_model(model_path)
	return getattr(model, attr, None)


def get_model(model_path):
	"""
	Returns model based on model_path as app_label.model_name
	"""
	try:
		app_label, model_name = model_path.split('.')
	except ValueError:
		raise ImproperlyConfigured("{0} must be of the form 'app_label.model_name'".format(model_name))
	try:
		model = apps.get_model(app_label, model_name)
	except LookupError:
		raise ImproperlyConfigured("{0} refers to model '{1}' that has not been installed".format(model_name, model_path))
	return model


def get_swapped_model(model_path):
	return get_model(model_path)


def human_join(l, conjunction='and'):
	"""
	Join a list in a human-friendly way
	E.G. ['Mary', 'John', 'Xavier'] => "Mary, John and Xavier"
	"""
	if len(l) == 0:
		return None
	if len(l) == 1:
		return l[0]
	return ' '.join([', '.join(l[:-1]), conjunction, l[-1]])


def is_int(s):
	try:
		int(s)
		return True
	except ValueError:
		return False


def mask_email(email):
	"Mask an email from scott+test@example.com as s***t+test@example.com"
	parts = email.split('@')
	parts[0] = parts[0].split('+')
	parts[0][0] = ''.join((parts[0][0][:1], '*' * (len(parts[0][0]) - 2), parts[0][0][-1:]))
	parts[0] = '+'.join(parts[0])
	return '@'.join(parts)


def percent_change(from_value, to_value):
	"""
	Calculate percent change from X to Y
	"""
	try:
		return int(round(((float(to_value) / float(from_value)) * 100) - 100))
	except ZeroDivisionError:
		return '∞'


def register_specs(generators, force=False):
	"""
	Register a list of specs with their appropriate spec id's
	and skip if that id is already registered by the project itself
	"""
	for gen in generators:
		if 'force' in gen or force:
			try:
				unregister.generator(gen[0])
			except NotRegistered:
				pass
		try:
			register.generator(gen[0], gen[1])
		except AlreadyRegistered:
			pass


class ReleaseNotes(object):
	cache_key = 'release-notes'

	def __init__(self, request={}, context={}):
		self.notes = []
		self.context = context
		self.context['request'] = request
		self.search()

	def all(self, start=None, end=None):
		"All of the release notes. Call this in templates"
		for note in self.notes[start:end]:
			yield note

	def count(self):
		"Count of release notes"
		return len(self.notes)

	def find_files(self, dir):
		"Scan through a specific directory and find and parse .html templates"
		files = []
		for f in os.listdir(dir):
			if f.endswith(".html"):
				date = self.parse_date(f[:8])
				filename = os.path.join(dir, f)
				if date:
					data = {
						'file': filename,
						'title': self.parse_title(f[8:-5]),
						'date': date,
						'template': self.parse_template(filename),
						'hash': md5(filename.encode()).hexdigest()
					}
					data['html'] = self.render(data)
					files.append(data)
		self.notes += files

	def parse_date(self, date_str):
		"Parse a date string from the filename"
		try:
			return datetime.datetime.strptime(date_str, "%Y%m%d")
		except ValueError:
			return False

	def parse_template(self, file):
		"Read a template from the file"
		with open(file, 'r') as f:
			return f.read()

	def parse_title(self, name):
		"Parse a title fron the filename"
		return name.replace('_', ' ').strip().title()

	def recent(self):
		"Recent notes, call this from the template"
		return self.all(end=15)

	def render(self, entry):
		"Render the given file as a template"
		tpl = Template(entry['template'])
		context = self.context.copy()
		context.update(entry)
		c = Context(context)
		return tpl.render(c)

	def render_all(self):
		for note in self.notes:
			note = self.render(note)

	def search(self):
		"Loop through each app and find release notes in them"
		if cache.get(self.cache_key):
			self.notes = cache.get(self.cache_key)
		else:
			for app in apps.get_app_configs():
				notes_dir = os.path.join(app.path, 'releasenotes')
				if os.path.exists(notes_dir):
					self.find_files(notes_dir)
			cache.set(self.cache_key, self.notes, 3600)
		self.sort()
		self.render_all()

	def sort(self):
		"sort by newest dated files first"
		self.notes = sorted(self.notes, key=lambda d: d['date'], reverse=True)

	def since(self, datetime):
		"Find release notes since this datetime"
		return [note for note in self.notes if note['date'] > datetime]


def source_name_as_path(generator):
	"""
	A namer that, given the following source file name::

		photos/thumbnails/bulldog.jpg

	will generate a name like this::

		/path/to/generated/images/photos/thumbnails/bulldog/5ff3233527c5ac3e4b596343b440ff67.jpg

	where "/path/to/generated/images/" is the value specified by the
	``IMAGEKIT_CACHEFILE_DIR`` setting.

	"""
	source_filename = getattr(generator.source, 'name', None)
	try:
		modified_time = time.ctime(os.path.getmtime(str(generator.source.file)))
	except FileNotFoundError:
		return ''

	if source_filename is None or os.path.isabs(source_filename):
		# Generally, we put the file right in the cache file directory.
		directory = settings.IMAGEKIT_CACHEFILE_DIR
	else:
		# For source files with relative names (like Django media files),
		# use the source's name to create the new filename.
		dirs = [settings.IMAGEKIT_CACHEFILE_DIR]
		filepath = os.path.splitext(source_filename)[0]

		# Reduce the amount of dirs under cache bucket
		if settings.SYFERADMIN_IMAGE_DIR_SPLIT:
			fileparts = list(os.path.split(filepath))
			filename = fileparts.pop()

			# Grab the first x characters of the filename as another directory
			fileparts.append(filename[:settings.SYFERADMIN_IMAGE_DIR_SPLIT])
			fileparts.append(filename)

			dirs.extend(fileparts)
		else:
			dirs.append(filepath)

		directory = os.path.join(*dirs)

	ext = suggest_extension(source_filename or '', generator.format)
	filehash = '%s%s' % (md5(generator.get_hash().encode('utf-8') + modified_time.encode('utf-8')).hexdigest(), ext)
	return os.path.normpath(os.path.join(directory, filehash))


def timestamp(datetime):
	"""
	Convert a datetime object to a millisecond UNIX timestamp
	"""
	return time.mktime(datetime.timetuple()) * 1000


def unique_list(items):
	"""
	Return a unique list that preserves order
	"""
	new_list = []
	for item in items:
		if item not in new_list:
			new_list.append(item)
	return new_list


def unique_slugify(instance, value, field='slug', queryset=None):
	"""
	Find the next avavilable slug name for a given model instance
	"""
	slug = slugify(value).replace('_', '-')
	if not queryset:
		queryset = instance.__class__._default_manager.all()

	# Exclude this instance
	if instance.pk:
		queryset = queryset.exclude(pk=instance.pk)

	# Find the next available slug
	next = 2
	new_slug = slug
	while queryset.filter(**{field: new_slug}):
		new_slug = '{0}-{1}'.format(slug, next)
		next += 1

	return new_slug


def user_factory():
	from syferadmin.models import User
	return User
