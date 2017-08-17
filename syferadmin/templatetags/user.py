from django_jinja import library
from ..utils import current_user as current_user_util


@library.global_function
def current_user():
	return current_user_util()
