from functools import partial
import httplib2
from oauth2client.client import AccessTokenRefreshError
import random
import time

from apiclient.discovery import build

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.urlresolvers import reverse

from ..models import Setting


def token_notify():
	"Delete the oauth token"
	Setting.objects.filter(key='Site.google_analytics_oauth_code').delete()
	# Too many threads run at once on this for get_or_create to only create one instance reliably D:
	time.sleep(random.randint(0, 100) / 100)
	renew, created = Setting.objects.get_or_create(key='Site.google_analytics_oauth_code_renew', defaults={'value': 'Token needs refreshing'})

	if created:
		scheme = 'https://' if settings.Site.enable_ssl else 'http://'
		url = ''.join([scheme, get_current_site(None).domain, reverse('reports_authorize')])


class CoreReporting(object):
	resource = 'ga'

	def __call__(self, *args, **kwargs):
		try:
			return self.endpoint(**kwargs).execute().get('rows')
		except AccessTokenRefreshError:
			# token_notify()
			pass

	@property
	def endpoint(self):
		storage = Setting.objects.get(key='Site.google_analytics_oauth_code')
		storage.type = 'credentials'
		credential = storage.decode()
		http = httplib2.Http()
		http = credential.authorize(http)
		endpoint = getattr(build('analytics', 'v3', http=http).data(), self.resource)()
		return partial(endpoint.get, ids='ga:{}'.format(settings.Admin.Reporting.google_analytics_view_id))


class RealTimeReporting(CoreReporting):
	resource = 'realtime'

	def __call__(self, *args, **kwargs):
		try:
			return self.endpoint(**kwargs).execute()
		except AccessTokenRefreshError:
			# token_notify()
			pass
