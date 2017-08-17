from django_jinja import library
from ..utils import current_region as current_region_util


@library.global_function
def current_region():
	return current_region_util()
