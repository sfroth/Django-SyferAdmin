from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.messages import success
from django.contrib.messages.api import MessageFailure
from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from .middleware.threadlocal import get_request
from .mixins import RegionalModel
from .models import Region, UserLogin, User


@receiver(m2m_changed)
def region_cascade(sender, instance, **kwargs):
	"""
	Upon adding or removing a region, also add/remove the region's children
	"""
	model = type(instance)
	action = kwargs.get('action', None)
	regions = kwargs.get('pk_set', None)
	related_model = kwargs.get('model', None)

	# Only for models that extend RegionalModel mixin
	if related_model is not Region or not issubclass(model, RegionalModel):
		return

	# Only for post_add/post_remove
	if action not in ('post_add', 'post_remove'):
		return

	for region_id in regions:
		region = Region.objects.get(pk=region_id)
		if region.children():
			for child in region.children():
				instance.regions.add(child) if action == 'post_add' else instance.regions.remove(child)


@receiver(post_save)
def invalidate_view_cache(sender, **kwargs):
	"""
	Invalidate any view caches that contain template.cache.`modelname`-`instance_id`
	"""
	instance = kwargs['instance']
	model = type(instance)

	if not hasattr(instance, 'id'):
		return

	cache_key = '*template.cache.{}*{}*'.format(model.__name__.lower(), instance.id)
	# Delete cache by pattern
	if hasattr(cache, 'delete_pattern'):
		cache.delete_pattern(cache_key)


@receiver(pre_save)
def pre_save_slug_lower(sender, **kwargs):
	"Force instances with slug fields to lower and replace underscores with dashes"
	instance = kwargs['instance']
	if hasattr(instance, 'slug'):
		instance.slug = instance.slug.lower().replace('_', '-')


@receiver(user_logged_out)
def display_logout_message(sender, request, **kwargs):
	try:
		success(request, 'Logged out')
	# Catch MessageFailure in case messages middleware is not loaded
	# which may occur during testing.
	except MessageFailure:
		pass


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
	"Log successful login attempts"
	log = UserLogin.create(request=request, successful=True, user=user)
	log.save()


@receiver(user_login_failed)
def log_failed_login(sender, credentials, **kwargs):
	"Log failed login attempts"
	request = get_request()
	try:
		user = User.objects.get(email=credentials['username'])
	except (User.DoesNotExist, User.MultipleObjectsReturned, KeyError):
		return

	log = UserLogin.create(request=request, successful=False, user=user)
	log.save()
