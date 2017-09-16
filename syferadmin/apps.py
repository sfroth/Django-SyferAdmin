import os
from appconf import AppConf
from django.apps import AppConfig
from django.conf import settings
from django.db.models import options

# Add additional Model Meta options
options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('related_admin_ordering', 'related_admin_search_fields')


# Supress non-essential warnings from inlinestyler
import cssutils
import logging
cssutils.log.setLevel(logging.CRITICAL)


class SyferAdminConfig(AppConfig):
	name = 'syferadmin'
	verbose_name = "SyferAdmin"

	def ready(self):
		from . import checks
		from . import receivers
		import tempfile
		from django.conf import settings
		tempfile.tempdir = settings.FILE_UPLOAD_TEMP_DIR
		load_admin_settings()


class SyferAdminConf(AppConf):
	COUNTRY_COOKIE_NAME = 'DetectedCountry'
	DASHBOARD_FILTER_TO_CURRENT_REGION = False  # Requires Custom Dimension configuration in GTM and GA
	DASHBOARD_MODULES = (
		('showcase top', ('store_snapshot',)),
		('split-col left', ('right_now', 'top_searches', 'order_trend')),
		('split-col right', ('sales_trend', 'traffic')),
		('showcase bottom', ('top_products',)),
	)
	EMAIL_BCC = []
	EXPORT_EXCEL = False
	FILTER_TO_CURRENT_REGION = False
	GEO_IP_PATH = os.path.join(settings.BASE_DIR, 'syferadmin', 'static', 'geo')
	GOOGLE_CLIENT_SECRET = os.path.join(os.path.dirname(__file__), 'services/google_client_secret.json')
	IMAGE_DIR_SPLIT = None
	REGION_COOKIE_NAME = 'RegionSetting'
	REGION_REDIRECTS = []
	SEARCH_MODELS = ()
	USER_NOTE_TYPES = None  # List of tuples for user note types
	USER_USERNAME_REGEX = r'^[\w.@+-]+$'


def load_admin_settings():
	from .settings import Settings

	APP_SETTINGS = {
		'Admin': {
			'date_format': {'type': 'text', 'admin': True, 'default': 'n/j/y h:ia', 'description': "The default date format for created/modified dates in tables"},
			'login_logo': {'type': 'text', 'default': "/static/syferadmin/img/admin-login-logo.png", 'description': "Logo to replace the title on the login screen (240x34 pixels max)"},
			'timezone': {'type': 'text', 'admin': True, 'default': "US/Pacific", 'description': "The default timezone for the admin (Olson format)"},
			# 'Reporting': {
			# 	'google_analytics_view_id': {'type': 'text', 'admin': True, 'name': 'Google Analytics View ID', 'description': 'Enter your Google Analytics View ID to enable GA-based reports on your dashboard', 'placeholder': 'XXXXXXXX'},
			# },
		},
		'Company': {
		# 	'address': {'type': 'textarea'},
		# 	'email': {'type': 'email'},
		# 	'hours': {'type': 'textarea'},
		# 	'legal_name': {'type': 'text', 'description': 'Legal company name. Example: The Company. Inc'},
			'name': {'type': 'text'},
		# 	'phone': {'type': 'tel'},
		# 	'toll_free_phone': {'type': 'tel', 'placeholder': '(555) 555 5555'},
		# 	'Social': {
		# 		'Facebook': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://facebook.com/example'},
		# 		},
		# 		'Google_Plus': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://plus.google.com/example'},
		# 		},
		# 		'Instagram': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://instagram.com/example'},
		# 		},
		# 		'Pinterest': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://pinterest.com/example'},
		# 		},
		# 		'Soundcloud': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'https://soundcloud.com/example'},
		# 		},
		# 		'Spotify': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://spotify.com/example'},
		# 		},
		# 		'Twitter': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://twitter.com/example'},
		# 		},
		# 		'Tumblr': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://tumblr.com/example'},
		# 		},
		# 		'Vimeo': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://vimeo.com/example'},
		# 		},
		# 		'Youtube': {
		# 			'show': {'type': 'bool'},
		# 			'url': {'type': 'url', 'name': 'URL', 'placeholder': 'http://youtube.com/example'},
		# 		},
		# 	},
		},
		'Site': {
			'enable_ssl': {'type': 'bool', 'name': 'Enable SSL?', 'admin': True},
			# 'google_tag_manager_container_id': {'type': 'text', 'admin': True, 'name': 'Google Tag Manager Container ID', 'placeholder': 'XXX-XXXXX'},
			# 'mode': {'type': 'select', 'default': 'dev', 'admin': True, 'description': 'Website Mode', 'options': [('dev', 'Development'), ('staging', 'Staging'), ('prod', 'Production')]},
			# 'site_title_separator': {'type': 'text', 'admin': True, 'name': 'Page Title Tag Item Separator', 'default': '/', 'description': 'Global site title tag separator.'},
		},
	}

	Settings.register(APP_SETTINGS)
