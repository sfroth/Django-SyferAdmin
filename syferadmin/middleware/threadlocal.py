"""
Make the request object available everywhere

Based on ThreadLocal from https://github.com/jedie/django-tools
"""
try:
	from threading import local
except ImportError:
	from django.utils._threading_local import local


_thread_locals = local()


def get_request():
	"Returns the request object for this thread"
	return getattr(_thread_locals, "request", None)


def get_request_attr(name):
	"Try to return request attr"
	request = get_request()
	if request:
		return getattr(_thread_locals, name, None)
	return None


class ThreadLocalMiddleware(object):
	"Simple middleware that adds the request object in thread local storage."

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		_thread_locals.request = request

		response = self.get_response(request)

		return response
