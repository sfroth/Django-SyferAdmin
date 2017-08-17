from django.conf import settings
from django.test import TestCase

from ..models import Region, Setting
from ..settings import Settings


class SettingsTestCase(TestCase):
	fixtures = ['syferadmin/tests/fixtures/region.json']

	def setUp(self):
		APP_SETTINGS = {
			'World': {
				'release_the_kracken': {'type': 'bool', 'name': 'Should the Kracken be unleashed upon the world?', 'admin': True, 'default': False},
			},
		}
		Settings.register(APP_SETTINGS)
		Settings.reload()
		self.region = Region.objects.first()

	def test_default(self):
		"Check default setting"
		self.assertEqual(False, settings.World.release_the_kracken)

	def test_setting_for_region(self):
		"Check for region setting"
		setting = Setting(key='World.release_the_kracken', region=self.region, value=True)
		setting.save()
		Settings.reload(region=self.region)
		self.assertEqual(True, settings.World.release_the_kracken)

	def test_find_setting_for_region(self):
		"Try to find setting for region and fallback to default"
		setting_default = Setting(key='World.release_the_kracken', region=None, value=True)
		setting_default.save()
		setting = Setting(key='World.release_the_kracken', region=self.region, value=False)
		setting.save()
		Settings.reload(region=self.region)
		# Seting for region
		self.assertEqual(False, Settings.find('World.release_the_kracken', region=self.region))
		setting.delete()
		Settings.reload(region=self.region)
		# Default save setting
		self.assertEqual(True, Settings.find('World.release_the_kracken', region=self.region))
		setting_default.delete()
		Settings.reload(region=self.region)
		# Default setting
		self.assertEqual(False, Settings.find('World.release_the_kracken', region=self.region))
