import logging
import re
import os

from django.apps import apps
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect as httpredirect
from django.utils import timezone

try:
	from django.contrib.gis.geoip import GeoIPA
except ImportError:
	pass

from ..models import Region
from ..settings import Settings


class RegionMiddleware(object):
	"""
	Middleware that detects & sets current region based on IP
	and inserts region data into request and templates.
	"""
	detected_country_code = None

	def __init__(self, get_response):
		self.cookie_name = settings.SYFERADMIN_REGION_COOKIE_NAME
		self.log = logging.getLogger('syferadmin')
		self.get_response = get_response

	def detect_region(self, request):
		try:
			self.detected_country_code = GeoIP(path=settings.SYFERADMIN_GEO_IP_PATH).country_code(request.META['REMOTE_ADDR'])
			self.log.debug("IP Detected Country for {}: {}".format(request.META['REMOTE_ADDR'], self.detected_country_code))
		except NameError as e:
			self.detected_country_code = ''
			self.log.debug("No Detected Country for {}".format(request.META['REMOTE_ADDR']))
		try:
			if self.detected_country_code:
				return Region.objects.get(countries__country_code=self.detected_country_code)
			raise Region.DoesNotExist
		except Region.DoesNotExist:
			try:
				return Region.objects.get(countries=None, parent__isnull=True)
			except Region.DoesNotExist:
				return Region.objects.first()

	def __call__(self, request):
		"Get region via GET override, session, or detect it if not set"
		# Check for a region override
		region_override = request.GET.get('region', None)
		if region_override:
			request.region = get_object_or_404(Region, slug=region_override)
			request.region.override = True
		else:
			try:
				# Check if the region was stored in a cookie, and use that
				request.region = Region.objects.get(pk=request.COOKIES[self.cookie_name])
			except (Region.DoesNotExist, ValueError, KeyError):
				# Cookie not set or invalid region selected, so detect the region and set it
				request.region = self.detect_region(request)
				request.region.override = True

		# Set detected country on request
		detected_country_code = self.detected_country_code or request.COOKIES.get(settings.SYFERADMIN_COUNTRY_COOKIE_NAME)
		request.detected_country = detected_country_code

		# Check for any redirects on this region
		for redirect in settings.SYFERADMIN_REGION_REDIRECTS:
			if redirect['region'] == request.region.slug and re.search(redirect['pattern'], request.path):
				response = httpredirect(redirect['destination'])
				response = self.set_region_cookies(request, response)
				return response

		is_admin = '/admin/' in request.path
		if is_admin and request.user.is_staff:
			# Force admin users into their region
			if not request.user.is_superuser and request.region not in request.user.regions.parents():
				request.region = request.user.regions.parents().first()
				request.region.override = True
			# Force admins in child regions to their parent
			if request.region.parent:
				request.region = request.region.parent
				request.region.override = True

		# Reload settings for region
		Settings.reload(request.region)

		# Timezone for region
		if request.region.timezone:
			timezone.activate(request.region.timezone)

		# Set locale cookie
		if hasattr(request, 'session'):
			if request.region.locale != request.session.get(settings.LANGUAGE_COOKIE_NAME, None):
				request.session[settings.LANGUAGE_COOKIE_NAME] = request.region.locale or settings.LANGUAGE_CODE

			# Region default language redirect
			if apps.is_installed('modeltranslation'):
				current_url = '{}{}{}'.format(request.path, '?' if request.GET else '', request.GET.urlencode())
				region_language_code = request.region.locale

				if not is_admin and region_language_code:
					# for non-admin requests, if region locale is set, redirect user to appropriate translation
					if os.path.isdir(os.path.abspath(os.path.join(settings.PROJECT_APP_PATH, 'locale'))):
						if not any(a for a in os.listdir(os.path.abspath(os.path.join(settings.PROJECT_APP_PATH, 'locale'))) if a.lower() == region_language_code.replace('-', '_').lower()):
							region_language_code = settings.LANGUAGE_CODE
					skip_language_check = False
					if region_language_code != settings.LANGUAGE_CODE and current_url.startswith('/{}/'.format(region_language_code)):
						skip_language_check = True
					if not skip_language_check:
						language_url = current_url
						for language, _ in settings.LANGUAGES:
							if language != settings.LANGUAGE_CODE and language_url.startswith('/{}/'.format(language)):
								language_url = language_url[len('/{}'.format(language)):]
						if region_language_code != settings.LANGUAGE_CODE:
							language_url = '/{}{}'.format(region_language_code, language_url)
						if current_url != language_url:
							return HttpResponseRedirect(language_url)
				elif is_admin:
					# don't allow translations on admin
					untranslated_url = None
					for language, _ in settings.LANGUAGES:
						if language != settings.LANGUAGE_CODE and current_url.startswith('/{}/'.format(language)):
							untranslated_url = current_url[len('/{}'.format(language)):]
					if untranslated_url:
						return HttpResponseRedirect(untranslated_url)

		response = self.get_response(request)

		if not getattr(request, 'region', None):
			return response

		response = self.set_region_cookies(request, response)
		return response

	def set_region_cookies(self, request, response):
		"Set the cookies specific to the selected region"

		if not getattr(request, 'region', None):
			return response

		# Set locale cookie
		if request.region.locale != request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, None):
			response.set_cookie(settings.LANGUAGE_COOKIE_NAME, request.region.locale)

		# Set the region cookie
		if request.region.id and hasattr(request.region, 'override'):
			self.log.debug("Setting region {}".format(request.region))
			response.set_cookie(self.cookie_name, request.region.id, max_age=3600 * 24 * 30)

			# Set the detected country code cookie
			if self.detected_country_code:
				response.set_cookie(settings.SYFERADMIN_COUNTRY_COOKIE_NAME, self.detected_country_code)

		return response
