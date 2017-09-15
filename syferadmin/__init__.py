import copy
from importlib import import_module

from django.core.urlresolvers import reverse
from django.apps import apps as django_apps
from django.http import Http404
from django.utils.module_loading import import_string, module_has_submodule


__version__ = '1.1.3'
default_app_config = 'syferadmin.apps.SyferAdminConfig'


def autodiscover():
	"""
	Override of autodiscover in django.contrib.admin
	"""

	import copy
	from django.conf import settings
	from .admin import site

	for app in settings.INSTALLED_APPS:
		mod = import_module(app)
		# Attempt to import the app's admin module.
		try:
			before_import_registry = copy.copy(site._registry)
			import_module('%s.admin' % app)
		except (Exception) as ex:
			# Reset the model registry to the state before the last import as
			# this import will have to reoccur on the next request and this
			# could raise NotRegistered and AlreadyRegistered exceptions
			# (see #8245).
			site._registry = before_import_registry

			# Decide whether to bubble up this error. If the app just
			# doesn't have an admin module, we can ignore the error
			# attempting to import it, otherwise we want it to bubble up.
			if module_has_submodule(mod, 'admin'):
				raise


class BaseSection():
	name = 'General'
	title = 'General'
	token = 'general'
	position = 0

	def __init__(self):
		self.children = []


class AdminSection(BaseSection):
	name = 'Admin'
	title = 'Admin Settings'
	token = 'settings'
	position = 100


class AlreadyRegistered(Exception):
	pass


class NotRegistered(Exception):
	pass


class EmailRegistry:

	def __init__(self):
		self._registry = {}

	def __iter__(self):
		for k in sorted(self._registry, key=lambda k: (self._registry[k].sort, self._registry[k].name)):
			yield self._registry[k]

	def get(self, label):
		try:
			return self._registry[label]
		except KeyError:
			raise NotRegistered('{} has not been registered'.format(label))

	def register(self, email):
		if email.label in self._registry:
			raise AlreadyRegistered('{} is already registered'.format(email.label))
		self._registry[email.label] = email

	def registered(self, label):
		return label in self._registry

	def unregister(self, email):
		try:
			del self._registry[email.label]
		except KeyError:
			raise NotRegistered('{} has not been registered'.format(email.label))


class Email:
	name = None
	sort = 5

	def get_email(self, **kwargs):
		return NotImplementedError('get_email not implemented on {}!'.format(self.__class__.__name__))

	def Http404(self):
		raise Http404('{} Not Found'.format(self.name or self.label))

	@property
	def label(self):
		return self.__class__.__name__

	def url(self):
		return reverse('emails', kwargs={'email_type': self.label})


emails = EmailRegistry()
