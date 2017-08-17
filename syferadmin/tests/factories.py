import factory
from factory.django import DjangoModelFactory as Factory

from .. import models


class RegionFactory(Factory):
	class Meta():
		model = models.Region
		django_get_or_create = ('slug',)

	name = 'United States'
	slug = 'us'
	timezone = 'America/Los_Angeles'
	countries = ['us']
