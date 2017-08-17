from django.forms.models import model_to_dict
from django.http import HttpResponse

from .. import json
from ..models import Video


def add(request):
	"Validate that the video exists and add it"

	result = {'success': False}
	result['videos'] = []

	if 'videos' in request.POST:
		for video_url in request.POST.get('videos').split(' '):
			video = Video()
			video.info(video_url)
			if video.type:
				result['videos'].append(model_to_dict(video))

	if result['videos']:
		result['success'] = True

	return HttpResponse(json.dumps(result), content_type='application/json')
