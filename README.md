Django Admin App
==============

Admin app to override and extend the default Django admin

# Installation

1. Install syferadmin `pip install -e git+ssh://git@github.com/sfroth/django-syferadmin.git#egg=syferadmin`
1. Make sure the following items are in your INSTALLED_APPS. syferadmin must come before django.contrib.admin
	- django.contrib.auth
	- django.contrib.contenttypes
	- django.contrib.sessions
	- django.contrib.sites
	- django.contrib.messages
	- django.contrib.staticfiles
	- mptt
	- syferadmin
	- django.contrib.admin
1. Set the auth model in settings.py `AUTH_USER_MODEL = 'syferadmin.User'`
1. Sync the database with `python manage.py migrate syferadmin`
1. Add the following to urls.py in your project
	- `import syferadmin`
	- `syferadmin.autodiscover()` Above the urlpatterns
	- `url(r'^admin/', include('syferadmin.urls')),` in urlpatterns
	- `url(r'^admin/', include(syferadmin.site.urls)),` in urlpatterns
1. Add the tmp dir for uploads in your repo root `mkdir tmp/uploads`
1. Add the following context processors before django request
    - syferadmin.context_processors.settings
    - syferadmin.context_processors.sections
1. Add the following middleware
    - syferadmin.middleware.threadlocal.ThreadLocalMiddleware
1. Add the following to settings.py `IMAGEKIT_SPEC_CACHEFILE_NAMER = 'syferadmin.utils.source_name_as_path'`
