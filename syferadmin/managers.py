from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models.query import QuerySet
from django.utils.timezone import now

from .mixins import RegionalManager, RegionalQuerySet, SchedulableManager, SchedulableQuerySet


class RegionQuerySet(QuerySet):

	def allows_shopping(self):
		return self.filter(warehouse__isnull=False)

	def children(self, region, include_self=False):
		"Children for this region"
		if include_self:
			return self.filter(models.Q(parent=region) | models.Q(pk=region.pk))
		return self.filter(parent=region)

	def multiple(self):
		"Are there multiple top level regions?"
		return self.parents().count() > 1

	def parents(self):
		"Top level regions only in the admin"
		return self.filter(parent=None, admin=True)


class RegionManager(models.Manager):

	def allows_shopping(self):
		return self.get_queryset().allows_shopping()

	def get_queryset(self):
		return RegionQuerySet(self.model)

	def children(self, region, include_self=False):
		return self.get_queryset().children(region, include_self)

	def multiple(self):
		"Are there multiple regions?"
		return self.get_queryset().multiple()

	def parents(self):
		return self.get_queryset().parents()


class UserManager(BaseUserManager):

	def _create_user(self, email, password, is_staff, is_superuser, **extra_fields):
		"""
		Creates and saves a User with the given username, email and password.
		"""
		email = self.normalize_email(email)
		user = self.model(email=email, is_staff=is_staff, is_active=True, is_superuser=is_superuser, last_login=now(), **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_user(self, email, password=None, **extra_fields):
		return self._create_user(email, password, False, False, **extra_fields)

	def create_superuser(self, email, password, **extra_fields):
		return self._create_user(email, password, True, True, **extra_fields)

	def public(self):
		return self.filter(is_active=True)


class SettingQueryset(QuerySet):

	def base(self):
		return self.filter(region__isnull=True)

	def for_region(self, region=None):
		# Use parent region settings
		region = region.parent or region
		return self.filter(region=region)
