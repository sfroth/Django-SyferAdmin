from __future__ import unicode_literals

from django.contrib.admin.utils import (lookup_field, display_for_field, display_for_value)
from django.contrib.admin.views.main import PAGE_VAR
from django.contrib.admin.templatetags.admin_modify import submit_row as django_submit_row
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.template import Library, Variable, VariableDoesNotExist

from syferadmin import json as json_lib
from syferadmin.admin import site

register = Library()


@register.filter
def concatenate(arg1, arg2):
	"""concatenate arg1 & arg2"""
	return str(arg1) + str(arg2)


@register.simple_tag()
def prev_page(cl):
	page = cl.paginator.page(cl.page_num + 1)
	if page.has_previous():
		return format_html('<a title="Previous Page" class="prev" href="{0}">Prev</a>', cl.get_query_string({PAGE_VAR: page.previous_page_number() - 1}))
	else:
		return format_html('<span class="prev disabled">Prev</span>')


@register.simple_tag()
def next_page(cl):
	page = cl.paginator.page(cl.page_num + 1)
	if page.has_next():
		return format_html('<a title="Next Page" class="next" href="{0}">Next</a>', cl.get_query_string({PAGE_VAR: page.next_page_number() - 1}))
	else:
		return format_html('<span class="next disabled">Next</span>')


@register.simple_tag()
def show_actions(cl, obj):
	f, attr, value = lookup_field('list_actions', obj, cl.model_admin)
	return display_for_value(value, getattr(attr, 'boolean', False))


@register.filter
def class_name(value):
	return value.__class__.__name__


@register.filter
def class_opts(value):
	return value._meta


@register.assignment_tag(takes_context=True)
def class_permission(context, cl, perm):
	model_name = cl._meta.model_name
	permission = '{}.{}_{}'.format(model_name, perm, model_name)
	return cl.__class__ in site._registry.keys() and 'perms' in context and permission in context['perms']


@register.filter
def class_verbose_name(value):
	return value._meta.verbose_name


@register.filter
def class_verbose_name_plural(value):
	return value._meta.verbose_name_plural


@register.filter
def class_content_type_id(value):
	return ContentType.objects.get_for_model(value).id


@register.filter
def future(obj):
	return timezone.now() < obj


@register.filter
def hash(object, attr):
	pseudo_context = {'object': object}
	try:
		value = Variable('object.%s' % attr).resolve(pseudo_context)
	except VariableDoesNotExist:
		value = None
	return value


@register.filter
def json(value):
	return mark_safe(json_lib.dumps(value))


@register.filter
def downcast(obj):
	if not hasattr(obj, 'content_type'):
		return obj

	model = obj.content_type.model_class()
	if model == obj.__class__:
		return obj
	return model.objects.get(pk=obj.pk)


@register.filter
def downcastable(obj):
	'Test if an object is able to be downcasted to a different type'
	if not hasattr(obj, 'content_type'):
		return False

	model = obj.content_type.model_class()
	if model == obj.__class__:
		return False
	return True


@register.filter
def active_link(cl, result):
	tag_title = 'Click to {}'.format('deactivate' if result.active else 'activate')
	tag_class = 'activate label {}'.format('active' if result.active else 'inactive')
	url = reverse(cl.model_admin.activation_url(), args=(result.id,))
	text = 'Active' if result.active else 'Inactive'
	return format_html('<a title="{0}" class="{1}" href="{2}">{3}</a>', tag_title, tag_class, url, text)


def items_for_sortable_result(cl, result, form):
	"""
	Generates the actual list of data for a sortable view.
	"""
	list_display = list(cl.list_display)
	if 'list_actions' in list_display:
		list_actions_index = list_display.index('list_actions')
		list_display = [list_display.pop(list_actions_index)] + list_display
	for field_name in list_display:
		tag_name = 'div'
		try:
			f, attr, value = lookup_field(field_name, result, cl.model_admin)
		except ObjectDoesNotExist:
			result_repr = 'EMPTY_CHANGELIST_VALUE'
		else:
			if value is None:
				yield ''
				continue
			if f is None:
				# No checkboxes in sortable plz
				if field_name == 'action_checkbox':
					continue
				allow_tags = getattr(attr, 'allow_tags', False)
				boolean = getattr(attr, 'boolean', False)
				if boolean:
					allow_tags = True
				result_repr = display_for_value(value, boolean)
				# Strip HTML tags in the resulting text, except if the
				# function has an "allow_tags" attribute set to True.
				if allow_tags:
					result_repr = mark_safe(result_repr)
			else:
				if isinstance(f.rel, models.ManyToOneRel):
					field_val = getattr(result, f.name)
					if field_val is None:
						result_repr = '(None)'
					else:
						result_repr = field_val
				else:
					result_repr = display_for_field(value, f)
		# By default the fields come from ModelAdmin.list_editable, but if we pull
		# the fields out of the form instead of list_editable custom admins
		# can provide fields on a per request basis
		if field_name == 'active':
			yield active_link(cl, result)
			continue
		if field_name in ['name', 'name_display']:
			tag_name = 'strong'
		if (form and field_name in form.fields and not (
				field_name == cl.model._meta.pk.name and
					form[cl.model._meta.pk.name].is_hidden)):
			bf = form[field_name]
			result_repr = mark_safe(force_text(bf.errors) + force_text(bf))
		yield format_html('<{0} class="{1}">{2}</{0}>', tag_name, field_name, result_repr)
	if form and not form[cl.model._meta.pk.name].is_hidden:
		yield format_html('<td>{0}</td>', force_text(form[cl.model._meta.pk.name]))


@register.inclusion_tag("admin/includes/field.html")
def render_field(field):
	return {'field': field}


@register.inclusion_tag("admin/change_list_results_sortable.html")
def result_list_sortable(cl, result):
	"""
	Displays results in a sortable list
	"""
	return {'cl': cl,
			'result': result,
			'items': items_for_sortable_result(cl, result, None)}


@register.inclusion_tag('admin/submit_line.html', takes_context=True)
def submit_row(context):
	"Overide django submit row to include admin context"
	ctx = django_submit_row(context)
	# Add cancel url
	ctx['cancel_url'] = context.get('cancel_url')
	return ctx


@register.filter
def lookup(d, key):
	try:
		return d[key]
	except (IndexError, KeyError):
		pass
	try:
		return d(key)
	except (TypeError):
		pass
	return ""
