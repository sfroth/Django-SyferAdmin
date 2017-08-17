from django.core.urlresolvers import resolve, reverse, Resolver404, NoReverseMatch
from django.utils.translation import activate, get_language
from django_jinja import library

from jinja2 import contextfunction


@library.global_function
@contextfunction
def change_lang(context, lang, *args, **kwargs):
	"""
	Get active page's url by a specified language
	Usage: {{ change_lang('en') }}
	"""
	path = context['request'].path

	# If url doesn't resolve, fallback to homepage
	try:
		url_parts = resolve(path)
	except Resolver404:
		url_parts = resolve('/')

	url = path
	cur_language = get_language()
	try:
		activate(lang)
		if url_parts.args or url_parts.kwargs:
			url = reverse(url_parts.view_name, args=url_parts.args, kwargs=url_parts.kwargs)
		else:
			url = reverse(url_parts.view_name)
	except NoReverseMatch:
		url = reverse('home')
	finally:
		activate(cur_language)

	return "%s" % url
