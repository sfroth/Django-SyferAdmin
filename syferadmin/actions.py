from django.contrib import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect


def batch_action(url, url_args, request):
	selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
	return HttpResponseRedirect('{0}?ids={1}'.format(reverse(url, args=url_args), ",".join(selected)))
