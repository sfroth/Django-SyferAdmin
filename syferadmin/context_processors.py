from copy import copy

from .admin import site
from .models import Region
from .settings import Settings


def regions(request):
	context = {
		'regions': Region.objects.all(),
		'region': request.region,
	}
	if request.user.is_staff:
		context.update({'user_regions': request.user.regions.parents() if not request.user.is_superuser else Region.objects.parents()})
	return context


def sections(request):
	"""
	Build admin navigation and pass to the template
	"""
	# Return if there was no match (in case of 404's, etc)
	if not request.resolver_match or not request.user.is_staff:
		return {}

	# Build navigation bar
	sections = [copy(section) for section in sorted(site.sections.values(), key=lambda section: section.position)]
	for section in sections:
		section.active = False
		section.children = sorted(section.children, key=lambda sub_section: sub_section['position'])
		# Check perms for subsection
		if request.user.is_authenticated() and not request.user.is_superuser:
			section.children = [sub_section for sub_section in section.children if request.user.has_perm(sub_section['perm'] if 'perm' in sub_section else '{}.change_{}'.format(*sub_section['app'].split('_')))]
		for sub_section in section.children:
			if 'url' not in sub_section:
				sub_section['url'] = 'admin:{}_changelist'.format(sub_section['app'])
			if 'add_url' not in sub_section and sub_section['admin'] and sub_section['admin'].has_add_permission(request):
				sub_section['add_url'] = 'admin:{}_add'.format(sub_section['app'])

			# If the url matches the app name, mark it active and derive side sections
			resolver_match = request.resolver_match.url_name and '{}_'.format(sub_section['app']) in request.resolver_match.url_name
			active_url_token = sub_section['active_url_token'] and sub_section['active_url_token'] in request.path
			if resolver_match or active_url_token:
				sub_section['active'] = True
				section.active = True
			else:
				sub_section['active'] = False

	return {'sections': sections}


def settings(request):
	"""
	Add all available settings to the template
	"""
	return {"settings": Settings.load('values', getattr(request, 'region', None))}
