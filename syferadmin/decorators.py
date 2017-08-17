from functools import wraps, partial
from django.conf import settings
from django.contrib.auth import decorators, REDIRECT_FIELD_NAME
from django.contrib.messages import error
from django.core.cache import cache
from django.utils.decorators import available_attrs
from django.utils.encoding import force_str
from django.utils.six.moves.urllib.parse import urlparse
from django.shortcuts import resolve_url

from .utils import current_region


def hash_args(*args, **kwargs):
	"""
	Generate hash for method args and kwargs.
	"""
	import hashlib
	values = []
	for arg in args:
		values.append(str(arg))
	for key, arg in kwargs.items():
			values.append('='.join((str(key), str(arg))))
	key = hashlib.md5("".join(values).encode('utf-8')).hexdigest()
	return key


def doublewrap(f):
	"""
	a decorator decorator, allowing the decorator to be used as:
	@decorator(with, arguments, and=kwargs)
	or
	@decorator
	"""
	@wraps(f)
	def new_dec(*args, **kwargs):
		if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
			# actual decorated function
			return f(args[0])
		else:
			# decorator arguments
			return lambda realf: f(realf, *args, **kwargs)

	return new_dec


@doublewrap
def cacheable(func, timeout=600, cache_key=None, create_hash=True):
	"""
	Decorator for caching method/function returns. Hashes pk for model methods and
	args for unique cache key.
	"""
	def _wrapper(*args, **kwargs):
		build_cache_key = [cache_key or func.__name__]

		region = current_region()
		if region:
			build_cache_key.append(region.slug)

		# Return uncached value for this request
		uncache = kwargs.pop('uncache', False)

		# Determine if this is a class method
		# and grab the instance pk
		argnames = func.__code__.co_varnames[:func.__code__.co_argcount]
		if (len(argnames) > 0 and
			argnames[0] == 'self' and
			hasattr(args[0], 'pk') and
			create_hash):
				build_cache_key.insert(0, args[0].__class__.__name__)
				build_cache_key.append(hash_args(_id=args[0].pk, *args, **kwargs))
		elif create_hash:
			build_cache_key.append(hash_args(*args, **kwargs))

		key = '-'.join(build_cache_key)

		result = 'expired'
		if uncache:
			# Delete current cached value
			cache.delete(key)
		else:
			# Get the cache by built key
			result = cache.get(key, 'expired')

		# No cached result, pass to method
		if result == 'expired':
			result = func(*args, **kwargs)
			cache.set(key, result, timeout)

		return result
	return _wrapper


class memoize(object):
	def __init__(self, func):
		self.func = func

	def __get__(self, obj, objtype=None):
		if obj is None:
			return self.func
		return partial(self, obj)

	def __call__(self, *args, **kw):
		obj = args[0]
		try:
			cache = obj.__cache
		except AttributeError:
			cache = obj.__cache = {}
		key = (self.func, args[1:], frozenset(kw.items()))
		try:
			res = cache[key]
		except KeyError:
			res = cache[key] = self.func(*args, **kw)
		return res


def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME, message=None):
	"""
	Override of https://github.com/django/django/blob/master/django/contrib/auth/decorators.py#L11
	wiht messaging capability.
	"""

	def decorator(view_func):
		@wraps(view_func, assigned=available_attrs(view_func))
		def _wrapped_view(request, *args, **kwargs):
			if test_func(request.user):
				return view_func(request, *args, **kwargs)
			path = request.build_absolute_uri()
			# urlparse chokes on lazy objects in Python 3, force to str
			resolved_login_url = force_str(
				resolve_url(login_url or settings.LOGIN_URL))
			# If the login url is the same scheme and net location then just
			# use the path as the "next" url.
			login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
			current_scheme, current_netloc = urlparse(path)[:2]
			if ((not login_scheme or login_scheme == current_scheme) and
					(not login_netloc or login_netloc == current_netloc)):
				path = request.get_full_path()
			if message:
				error(request, message)
			from django.contrib.auth.views import redirect_to_login
			return redirect_to_login(
				path, resolved_login_url, redirect_field_name)
		return _wrapped_view
	return decorator


def login_required_with_message(function=None, *args, **kwargs):
	"""
	Override of https://github.com/django/django/blob/master/django/contrib/auth/decorators.py#L41
	with messaging capability.
	"""
	actual_decorator = user_passes_test(lambda u: u.is_authenticated(), *args, **kwargs)
	if function:
		return actual_decorator(function)
	return actual_decorator

# Monkey patch Django's existing login required function
setattr(decorators, 'login_required', login_required_with_message)
