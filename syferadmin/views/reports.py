from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from syferadmin.csv import UnicodeWriter
from .. import json
from ..reports import Report
from ..forms import ReportDatesForm
from ..tasks import run_report, export_report


@staff_member_required
@permission_required('syferadmin.can_view_reports')
def report_detail(request, token):
	report_request = {
		'report': request.GET,
		'region': request.region,
		'user': request.user,
	}
	report = Report.get_report(report_request, token)
	context = {
		'report': report,
		'form': ReportDatesForm(),
		'report_title': report.title
	}

	return TemplateResponse(request, 'reports/detail.html', context)


@staff_member_required
def detail(request, token):
	data = None
	# Creating a json object here cause the standard request obj is not pickleable
	report_request = {
		'report': request.GET,
		'region_id': request.region.id,
		'user_id': request.user.id,
	}
	if request.is_ajax():
		# Delaying the report due to timeouts for heavy reports
		job = run_report.delay(report_request, token)
		# Return the report result or the id of the job if celery is running
		if job.result:
			data = job.result()
		else:
			request.session['task_id'] = job.id
			data = {'job_id': job.id}
	else:
		data = run_report(report_request, token, direct=True)

	return HttpResponse(json.dumps(data), content_type="application/json")


@csrf_exempt
def poll_report_state(request):
	""" A view to report the progress to the user """
	if not request.is_ajax():
		raise SuspiciousOperation("No access.")
	try:
		from celery.result import AsyncResult
		result = AsyncResult(request.POST['task_id'])
	except (ImportError, KeyError):
		ret = {'error': 'No optimisation (or you may have disabled cookies).'}
		return HttpResponse(json.dumps(ret))
	try:
		if result.ready():
			if(result.state == 'SUCCESS'):
				ret = {'status': 'solved'}
				# replace this with the relevant part of the result
				ret.update({'result': result.result})
			else:
				ret = {'error': 'This report had a little trouble completing. Please try again.'}
		else:
			ret = {'status': 'waiting'}
	except AttributeError:
		ret = {'error': 'Cannot find an optimisation task.'}
		return HttpResponse(json.dumps(ret), content_type="application/json")
	return HttpResponse(json.dumps(ret), content_type="application/json")


@staff_member_required
def export(request, token, export_as='csv'):
	if request.is_ajax():
		# Creating a json object here cause the standard request obj is not pickleable
		report_request = {
			'report': request.GET,
			'region': request.region,
			'user': request.user,
		}
		# Delaying the report due to timeouts for heavy reports
		job = export_report.delay(report_request, token, export_as)
		# Return the report result or the id of the job if celery is running
		if job.result:
			data = job.result
		else:
			request.session['task_id'] = job.id
			data = {'job_id': job.id}

	return HttpResponse(json.dumps(data), content_type="application/json")
