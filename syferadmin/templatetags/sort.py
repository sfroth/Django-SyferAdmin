from collections import OrderedDict
from django import template

register = template.Library()
TemplateSyntaxError = template.TemplateSyntaxError


@register.filter(name='sort')
def listsort(value):
	if isinstance(value, dict):
		new_dict = OrderedDict()
		key_list = value.keys()
		key_list.sort()
		for key in key_list:
			new_dict[key] = value[key]
		return new_dict
	elif isinstance(value, list):
		new_list = list(value)
		new_list.sort()
		return new_list
	else:
		return sorted(value, key=lambda x: (x.key))
