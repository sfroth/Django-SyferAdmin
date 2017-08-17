from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse

from ..utils import ReleaseNotes


@staff_member_required
def recent(request):
	r = ReleaseNotes(request)
	context = {
		'releasenotes': r,
	}

	return TemplateResponse(request, 'releasenotes/releasenotes.html', context)


@staff_member_required
def archive(request):
	r = ReleaseNotes(request)
	context = {
		'releasenotes': r,
	}

	return TemplateResponse(request, 'releasenotes/releasenotes.html', context)
