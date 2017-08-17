import collections
from copy import deepcopy

from django.conf import settings
from django.db import connection, utils

from .models import Setting
from .utils import dict_merge


class SettingGroup(object):

	def __init__(self, key, children):
		self.title = key
		self.key = key
		self.children = children

	def __getattr__(self, name):
		try:
			return self.children[name]
		except KeyError:
			raise AttributeError

	def __iter__(self):
		for setting in self.children.values():
			yield setting

	@property
	def count(self):
		return sum([getattr(setting, 'count', 1) for setting in self])

	@property
	def modified(self):
		dates = [setting.modified for setting in self if setting.modified]
		return max(dates) if dates else None


class Settings(object):
	default_settings = {}

	@classmethod
	def add_to_project(cls, user_settings):
		"Make all user settings accessible in django settings"
		for group in user_settings.children.keys():
			setattr(settings, group, getattr(user_settings, group))

	@classmethod
	def find(cls, key, region=None):
		"""
		Try to find a setting by key and region.

		While settings are automatically loaded for the current request
		context, sometimes we need region specific settings. For example,
		processing an order in another region.
		"""
		setting = None
		defaults = cls.find_defaults(key)
		# Find region setting
		if region:
			setting = Setting.objects.for_region(region).filter(key=key).first()
		# Fallback to default saved setting
		if setting is None:
			setting = Setting.objects.filter(key=key, region=None).first()
		# Fallback to request context setting
		if setting is None:
			setting = defaults.get('default', None)
		if hasattr(setting, 'get_value'):
			# Setup defaults for setting
			for attribute, default in defaults.items():
				setattr(setting, attribute, default)
			return setting.get_value()
		return setting

	@classmethod
	def find_defaults(cls, key):
		"Look through default_settings for key"
		keys = key.split('.')
		paths = cls.default_settings
		found = 0
		for k in keys:
			if k in paths:
				found += 1
				paths = paths[k]
		if found == len(keys):
			return paths

	@classmethod
	def load(cls, returns='objects', region=None):
		"Return all default and database settings as a nested SettingGroup"
		overrides = {}

		# When initializing the project settings might not exist yet.
		if 'syferadmin_setting' in connection.introspection.table_names():
			# Since we load settings in confs any queryset filtering done here
			# will break all the things. So, load the base settings at first
			# then reload with the region once we have it in region middleware.
			for model in Setting.objects.all():
				if not model.region_id:
					overrides[model.key] = model

			if region:
				for model in Setting.objects.for_region(region):
					overrides[model.key] = model

		return cls.map(deepcopy(cls.default_settings), overrides, returns)

	@classmethod
	def map(cls, mapping, overrides, returns='objects', full_key=None, key=None):
		"""
		Convert mappings to settings recursively.
		Inspired by https://gist.github.com/hangtwenty/5960435
		"""
		full_key = ".".join((full_key, key)) if full_key else key
		if isinstance(mapping, collections.Mapping) and 'type' not in mapping:
			for k, value in mapping.items():
				mapping[k] = cls.map(value, overrides, returns, full_key, k)
			return SettingGroup(key, mapping)
		mapping['key'] = full_key
		setting = Setting(**mapping)
		if full_key in overrides:
			setting.value = overrides[full_key].value
			setting.modified = overrides[full_key].modified
		else:
			setting.value = None
		return setting.get_value() if returns == 'values' else setting

	@classmethod
	def register(cls, mapping):
		"Register a mapping of available user settings"
		cls.default_settings = dict_merge(mapping, cls.default_settings)
		cls.reload()

	@classmethod
	def reload(cls, region=None):
		try:
			cls.add_to_project(cls.load('values', region))
		except utils.OperationalError:
			pass
