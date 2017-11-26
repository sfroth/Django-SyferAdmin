import json

from django.http import HttpResponse, Http404

from .helpers import UploadedFile


def add(request):
	"Temporarily save an uploaded file"

	# Small hack due to fineuploader not changing the standard parameter names
	request.POST._mutable = True
	if 'qquuid' in request.POST:
		request.POST['uuid'] = request.POST['qquuid']
	if 'qqtotalfilesize' in request.POST:
		request.POST['totalfilesize'] = request.POST['qqtotalfilesize']
	request.POST._mutable = False

	if 'file' not in request.FILES or 'uuid' not in request.POST:
		raise Http404

	result = {'success': False}
	temp_file = UploadedFile.create(request.POST['uuid'], request.FILES['file'])
	if temp_file.valid():
		try:
			temp_file.save()
			result = {'success': True, 'name': temp_file.name, 'path': temp_file.path, 'uuid': temp_file.uuid, 'type': temp_file.file_type}
			try:
				result['thumb'] = temp_file.thumb.url
			except AttributeError:
				pass
		except IOError as exc:
			result['message'] = exc.strerror
	else:
		result['message'] = 'Invalid file format!'

	return HttpResponse(json.dumps(result))


def check(request, uuid):
	"""
	Check status of an uploaded file

	Used mainly for checking the result of a video encoding process.
	"""
	temp_file = UploadedFile.create(uuid)
	result = {'exists': temp_file.exists()}
	if temp_file.file_type == 'video':
		result['encoded'] = temp_file.is_encoded()
	return HttpResponse(json.dumps(result))


def delete(request, uuid):
	"Delete a temporary file"
	temp_file = UploadedFile.create(uuid)
	try:
		result = {'success': temp_file.remove()}
	except Exception:
		result = {'success': False}
	return HttpResponse(json.dumps(result))
