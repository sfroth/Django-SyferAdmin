from distutils.version import StrictVersion
from django.core import checks


@checks.register()
def required_apps(app_configs, **kwargs):
	errors = []

	apps = (
		('django', '1.11.3'),
	)

	for app, version in apps:
		try:
			module = __import__(app)
			assert StrictVersion(module.__version__) >= StrictVersion(version)
		except (ImportError, AssertionError, AttributeError):
			errors.append(
				checks.Critical(
					'Make sure version {} of {} is installed'.format(version, app),
					id='syferadmin',
				)
			)

	return errors
