from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect

from oauth2client import client
from oauth2client.contrib import xsrfutil

from ..models import Setting


@staff_member_required
def authorize(request):
	"Request OAuth permission"
	oauth_flow = flow(request)
	oauth_flow.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
	# Need to specify access_type=offline to get a refresh_token back
	# which is needed to subsequently obtain new oauth tokens when the current access_token expires
	oauth_flow.params['access_type'] = 'offline'
	if Setting.objects.filter(key='Site.google_analytics_oauth_code_renew').exists():
		# we've already authed with force so subsequent approvals will happen automatically
		oauth_flow.params['approval_prompt'] = 'auto'
	else:
		# approval_prompt must be set to explicitly to force ask the user for offline access
		# (which is necessary to obtain the refresh_token) for the first time
		oauth_flow.params['approval_prompt'] = 'force'
	authorize_url = oauth_flow.step1_get_authorize_url()
	return redirect(authorize_url)


@staff_member_required
def authorized(request):
	"OAuth permission granted, set returned credentials"
	oauth_flow = flow(request)
	if not xsrfutil.validate_token(settings.SECRET_KEY, request.GET['state'].encode(), request.user):
		return HttpResponseBadRequest()
	credential = oauth_flow.step2_exchange(request.GET)
	# delete the renew token flag
	Setting.objects.filter(key='Site.google_analytics_oauth_code_renew').delete()
	storage, created = Setting.objects.get_or_create(key='Site.google_analytics_oauth_code')
	storage.value = credential
	storage.type = 'credentials'
	storage.save()
	return redirect('admin:dashboard')


def flow(request):
	"Shortcut to OAuth flow creation"
	return client.flow_from_clientsecrets(settings.SYFERADMIN_GOOGLE_CLIENT_SECRET,
		scope=[
			'https://www.googleapis.com/auth/analytics',
			'https://www.googleapis.com/auth/analytics.readonly'],
		redirect_uri=request.build_absolute_uri(reverse('reports_authorized')))
