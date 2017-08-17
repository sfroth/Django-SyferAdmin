import logging

from django import http
from django.contrib.messages import success
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse


def batch_to(request, model, modify_func, form, template='admin/batch_modify_action.html'):
	"""Batch modify objects

	Arguments:
	request 		-- Request object
	model 			-- Model to be modified
	modify_func 	-- Function to be called with arguments (items, form_data) that should make the modification
	form 			-- Form with additional info for the user to fill out
	"""
	return_url = reverse('admin:{}_{}_changelist'.format(model._meta.app_label, model._meta.verbose_name))
	item_ids = request.GET.get('ids', '')
	items = model.objects.filter(pk__in=item_ids.split(','))

	if request.method == 'POST':
		form = form(request.POST)
		if form.is_valid():
			success(request, modify_func(items, form.cleaned_data))
			return redirect(return_url)
	else:
		form = form()

	context = {
		'form': form,
		'items': items,
		'return_url': return_url,
	}

	return TemplateResponse(request, template, context)


def error(request, error_code='404', context={}, template_name='errors/error.jinja'):
	error_map = {
		'301': 'Moved Permanently',
		'302': 'Found',
		'304': 'Not Modified',
		'307': 'Temporary Redirect',
		'400': 'Bad Request',
		'401': 'Unauthorized',
		'403': 'Forbidden',
		'404': 'Not Found',
		'405': 'Method Not Allowed',
		'409': 'Conflict',
		'410': 'Gone',
		'418': "I'm A Teapot",
		'420': 'Enhance Your Calm',
		'500': 'Internal Server Error',
		'502': 'Bad Gateway',
		'503': 'Service Unavailable',
		'504': 'Gateway Timeout',
		'default': 'Unknown',
	}

	context['error_code'] = error_code
	context['reason_phrase'] = error_map[error_code] if error_code in error_map else error_map['default']
	response = http.HttpResponse(render(request, template_name, context), status=error_code)
	response.streaming = False
	response.status_code = context['error_code']
	response.reason_phrase = context['reason_phrase']
	return response


def waf_denied(request):
	"Web Application Firewall error page"
	logger = logging.getLogger(__name__)

	context = {
		'page': request.build_absolute_uri(),
		'host': request.get_host(),
		'ip': request.META.get('REMOTE_ADDR', 'N/A'),
		'event': request.GET.get('event_id', 'N/A'),
		'session': request.GET.get('session_id', 'N/A'),
		'user': getattr(request, 'user', 'N/A'),
	}

	logger.error('WAF Denied for {c[host]} Event ID: {c[event]} with IP={c[ip]}&USER={c[user]}'.format(c=context))
	return TemplateResponse(request, 'errors/waf_denied.jinja', context=context, status=403)
