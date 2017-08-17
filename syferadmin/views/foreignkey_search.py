from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden, HttpResponseServerError, JsonResponse


def default_formatter(r):
	return str(r)


def ajax_search(request, content_type_id):
	term = getattr(request, request.method).get('term', None)

	if None in (term, content_type_id):
		return HttpResponseServerError('Term and content type required')

	try:
		model = ContentType.objects.get(pk=content_type_id).model_class()
	except ContentType.DoesNotExist:
		return HttpResponseServerError('That content type is not allowed')

	if not hasattr(model, 'foreignkey_search'):
		return HttpResponseServerError('That content type is not allowed')

	if hasattr(model, 'has_foreignkey_search_permission') and not model.has_foreignkey_search_permission(request, term):
		return HttpResponseForbidden('You are not allowed to do that')

	start = (int(request.GET.get('page', 1)) - 1) * 30

	qs = model.foreignkey_search(request, term)
	count = qs.count()
	results = [{'pk': r.pk, 'value': str(r), 'display': r.foreignkey_search_formatter() if hasattr(r, 'foreignkey_search_formatter') else str(r)} for r in qs[start:start + 30]]

	return JsonResponse({'results': results, 'term': term, 'content_type_id': content_type_id, 'count': count})
