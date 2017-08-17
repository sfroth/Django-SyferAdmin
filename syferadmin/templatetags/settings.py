from django_jinja import library


@library.global_function
def settings_value(name):
	"Return django setting or syferadmin setting or None"
	from django.conf import settings
	setting = settings

	# Split settings by period
	chunks = name.split('.')

	# Loop through setting chunks until we arrive at the desired setting
	for chunk in chunks:
		setting = getattr(setting, chunk, None)

	return setting


@library.filter
def installed(app):
	"Check to see if this app is installed"
	from django.apps import apps
	return apps.is_installed(app)
