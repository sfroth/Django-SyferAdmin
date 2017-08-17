from functools import reduce
import operator
import re

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.http import HttpResponse

from .. import json


class Parser(object):
	"""Search query parser

	Returns list of terms found in search query.
	"""
	KEY_TERMS_RE = re.compile(r'(?:^| )([a-z_]+):"([^"]+)"(?:$)?')
	MULTI_TERMS_RE = re.compile(r'(?:^| )"((?:\d+"|[^"])+)"(?:$)?')
	TERMS_RE = re.compile(r'[\s,/]+')

	@classmethod
	def terms(cls, query):
		terms = []
		if not query:
			return terms
		terms += cls.MULTI_TERMS_RE.findall(query)
		query = cls.MULTI_TERMS_RE.sub('', query)
		if query:
			terms += cls.TERMS_RE.split(query)
		return [term for term in terms if term]


@staff_member_required
def lookup(request):
	"""
	Find relatable objects by content type.
	"""
	result = {
		'success': False,
		'results': []
	}

	# Get requested content_type & model
	content_type_id = request.GET.get('content_type_id')
	content_type = ContentType.objects.get(pk=content_type_id)
	model = content_type.model_class()
	objects = model.objects.all()

	# Order models if necessary
	try:
		objects = objects.order_by(*model._meta.related_admin_ordering)
	except AttributeError:
		pass

	# Parse search terms
	search_terms = Parser.terms(request.GET.get('search'))
	if search_terms:
		search_fields = getattr(model._meta, 'related_admin_search_fields', ['name'])
		conditions = []
		for term in search_terms:
			conditions.append(reduce(operator.or_, [Q(**{field if '__exact' in field else '{}__icontains'.format(field): term}) for field in search_fields]))
		objects = objects.filter(reduce(operator.and_, conditions))

	# Exclude object ID's
	exclusions = request.GET.get('exclude')
	if exclusions:
		objects = objects.exclude(pk__in=[int(id_num) for id_num in exclusions.split(',')])

	paginator = Paginator(objects.distinct(), 50)

	try:
		objects = paginator.page(request.GET.get('page', 1))
	except EmptyPage:
		objects = paginator.page(paginator.num_pages)

	if objects:
		result['pages'] = paginator.num_pages
		result['total'] = paginator.count
		result['success'] = True
		for item in objects:
			item_dict = {
				'id': item.id,
				'name': getattr(item, 'related_admin_name', item.name),
				'thumb': item.admin_thumb().url if hasattr(item, 'admin_thumb') and item.admin_thumb() else None,
				'content_type_id': content_type_id,
				'active': item.active if hasattr(item, 'active') else True,
				'regions': item.region_display() if hasattr(item, 'region_display') else None,
			}

			if hasattr(item, 'on_hand'):
				item_dict['quantity'] = item.available_quantity() if hasattr(item, 'available_quantity') else item.on_hand()

			item_dict.update(getattr(item, 'related_admin_extra_data', {}))
			result['results'].append(item_dict)

	return HttpResponse(json.dumps(result), content_type='application/json')
