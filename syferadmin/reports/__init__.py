from __future__ import unicode_literals, division
from importlib import import_module
from datetime import datetime
import pytz
import copy

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.forms.widgets import Media
from django.http import Http404
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils import dateparse

from ..services import google
from ..utils import timestamp
from syferadmin.models import Region, User


class ReportManager(object):
	reports = []
	unregistered = []

	@classmethod
	def all(cls):
		return cls.reports

	@classmethod
	def withdetail(cls):
		reports = [report for report in cls.reports if type(report) not in cls.unregistered]
		return [i for i in reports if hasattr(i, 'detail') and i.required_params is None]

	@classmethod
	def filter(cls, report_list):
		reports = [report for report in cls.all() if report.token in report_list]
		reports.sort(key=lambda x: report_list.index(x.token))
		return reports

	@classmethod
	def get(cls, token):
		try:
			return next(report for report in cls.reports if report.token == token)
		except StopIteration:
			raise Report.DoesNotExist('Report {} not found!'.format(token))

	@staticmethod
	def load_from_apps():
		for app_name in settings.INSTALLED_APPS:
			try:
				import_module('.reports', app_name)
			except ImportError:
				pass

	@classmethod
	def register(cls, reports):
		if not isinstance(reports, list):
			reports = [reports]
		cls.reports.extend(reports)

	@classmethod
	def registered(cls, report):
		return report in cls.reports or any([True for instance in cls.reports if isinstance(instance, report)])

	@classmethod
	def unregister(cls, reports):
		if not isinstance(reports, list):
			reports = [reports]
		cls.unregistered.extend(reports)


class Report(object):
	title = 'Untitled Report'
	compare_period = None
	dimensions = []
	sort = None
	show_record_count = False
	max_results = None
	template = 'reports/graph.html'
	objects = ReportManager
	DoesNotExist = ObjectDoesNotExist
	date_dependent = True
	required_params = None
	optional_params = None
	date_ranges = ('day', 'week', 'month', 'year', 'custom')

	def __init__(self, start_date=None, end_date=None, period=None):
		self.start_date = start_date
		self.end_date = end_date
		# Some users don't understand what dates are. Flip the dates if necessary
		if self.start_date and self.start_date > self.end_date:
			self.start_date = end_date
			self.end_date = start_date
		self.service = google.CoreReporting()

	@property
	def date_range(self):
		if not self.start_date or not self.end_date:
			return None
		time_delta = self.end_date - self.start_date
		# Round to nearest day
		return timedelta(days=round(time_delta.total_seconds() / (3600 * 24)))

	@classmethod
	def get_report(cls, request_data, token):
		try:
			if 'region_id' in request_data:
				request_data['region'] = Region.objects.get(id=request_data['region_id'])
			if 'user_id' in request_data:
				request_data['user'] = User.objects.get(id=request_data['user_id'])
			report = copy.copy(cls.objects.get(token=token))  # using copy because the rest of this method was modifying in-memory report
			# Set incoming parameters on report
			report.set_request(request_data)
		except((IndexError, MultiValueDictKeyError)):
			raise Http404('Report not found!')
		return report

	@property
	def media(self):
		if hasattr(self, 'Media'):
			return Media(self.Media)

	def run(self, start_date=None, end_date=None, filters=None):
		start_date = start_date or self.start_date
		end_date = end_date or self.end_date
		kwargs = {
			'start_date': start_date.strftime('%Y-%m-%d'),
			'end_date': end_date.strftime('%Y-%m-%d'),
			'metrics': ','.join([m[1] for m in self.metrics]),
			'dimensions': ','.join(self.dimensions),
			'sort': self.sort,
			'max_results': self.max_results,
			'filters': filters,
		}
		key_params = {'start_date': start_date, 'end_date': end_date, 'token': self.token, 'filters': filters}
		key = hash(frozenset(key_params.items()))
		result = cache.get(key)
		if not result:
			result = self.service(**kwargs)
			cache.set(key, result, 3600)
		return result

	@cached_property
	def token(self):
		return slugify(self.title).replace('-', '_')

	@property
	def url(self):
		return getattr(self, 'external_url', reverse('{}_report'.format(self.token)))

	def set_request(self, data):
		self.request = data
		report = data.get('report')
		if report.get('range'):
			self.selected_range = report.get('range', 'custom')
			now = datetime.now(data.get('region').tzinfo)
			if report.get('range') == 'day':
				self.start_date = now
				self.end_date = self.start_date
			elif report.get('range') == 'week':
				self.start_date = (now - timedelta(days=6))
				self.end_date = now
			elif report.get('range') == 'month':
				self.start_date = (now - timedelta(days=30))
				self.end_date = now
			elif report.get('range') == 'year':
				self.start_date = (now - timedelta(days=365))
				self.end_date = now

			self.start_date = dateparse.parse_datetime(report.get('start_date') + ' 00:00:00')
			self.end_date = dateparse.parse_datetime(report.get('end_date') + ' 23:59:59')

			# Set the specific times
			self.start_date = self.start_date.replace(hour=0, minute=0, second=0)
			self.end_date = self.end_date.replace(hour=23, minute=59, second=59)
			# Localize the timezones if they are not already
			if not getattr(self.start_date, 'tzinfo', None):
				self.start_date = pytz.timezone(str(data.get('region').timezone)).localize(self.start_date, is_dst=None)
			if not getattr(self.end_date, 'tzinfo', None):
				self.end_date = pytz.timezone(str(data.get('region').timezone)).localize(self.end_date, is_dst=None)

			# Flip the dates if people don't understand how time works
			if self.start_date > self.end_date:
				self.start_date, self.end_date = self.end_date, self.start_date

		self.params = {}
		if self.required_params is not None:
			for param in self.required_params:
				# this should throw a MultiValueDictKeyError if key doesn't exist
				self.params[param] = report[param]
		if self.optional_params is not None:
			for param in self.optional_params:
				if param in report and report[param]:
					self.params[param] = report[param]

		if report.__contains__('fields') and report['fields'] and hasattr(self, 'field_options'):
			self.fields_selected = report['fields'].split(',')

		if hasattr(self, 'update'):
			self.update()


class IncrementalReport(Report):

	def run(self, *args, **kwargs):
		if self.date_range and self.date_range.days < 7:
			self.dimensions = ['ga:nthHour']
			self.increment = relativedelta(hours=1)
		elif self.date_range and self.date_range.days <= 32:
			self.dimensions = ['ga:nthDay']
			self.increment = relativedelta(days=1)
		else:
			self.dimensions = ['ga:nthWeek']
			self.increment = relativedelta(days=7)
		if hasattr(self, 'add_dimensions'):
			self.dimensions = self.dimensions + self.add_dimensions
		return super(IncrementalReport, self).run(*args, **kwargs)

	def translate_date(self, val):
		return timestamp(self.start_date.replace(hour=0, minute=0, second=0) + self.increment * val)


class CustomerReport(Report):

	@staticmethod
	def customer(obj):
		if hasattr(obj, 'user') and obj.user:
			return """<a href="{2}">{0}<br>{1}</a>""".format(obj.user.name, obj.user.email, reverse('admin:customers_customer_change', args=(obj.user.id,)))
		elif isinstance(obj, User):
			return """<a href="{2}">{0}<br>{1}</a>""".format(obj.name, obj.email, reverse('admin:customers_customer_change', args=(obj.id,)))
		elif isinstance(obj, dict) and 'user__name' in obj and 'user__email' in obj and 'user__pk' in obj:
			return """<a href="{2}">{0}<br>{1}</a>""".format(obj['user__name'], obj['user__email'], reverse('admin:customers_customer_change', args=(obj['user__pk'],)))
		elif isinstance(obj, dict) and 'user__name' in obj:
			return obj['user__name'].name
		return None


class FilterOption(object):
	"Acts as an iterator with additional settings for filter options"
	show_all = True

	def __init__(self, data, show_all=True):
		self.data = data
		self.show_all = show_all

	def __iter__(self):
		return iter(self.data)


class FilteredReport(Report):
	fields_selected = []
	filter_current_region = settings.SYFERADMIN_FILTER_TO_CURRENT_REGION

	@property
	def filters(self):
		return None

	@property
	def optional_params(self):
		return [f[1] for f in self.filters]

	def filter_option_list(self):
		if not hasattr(self, '_filter_option_list'):
			# set of fields. This needs to be included in all queries
			fields = []
			for selected in self.fields_selected:
				fields.append(selected)
			fields = ','.join(fields)

			self._filter_option_list = {}
			options = self.filter_options()
			has_params = hasattr(self, 'params')

			# loop over filters
			# for each filter, loop over options
			# for each option, build querystring
			# querystring for an option is:
			# all selected options, minus this option
			# if this option is not selected, add to options
			# plus fields
			for fltr in self.filters:
				filter_key = fltr[1]
				filter_query = ''
				if has_params:
					for key, val in self.params.items():
						if key != filter_key:
							filter_query = '{}&{}={}'.format(filter_query, key, val)
				if filter_key == 'site_region':
					# Use 'all' param for regions
					if not has_params or filter_key not in self.params:
						selected = not self.filter_current_region
					else:
						selected = self.params.get(filter_key) == 'all'
					self._filter_option_list[filter_key] = [{'query': '?fields={}{}'.format(fields, '&{}=all'.format(filter_key)), 'text': 'All', 'selected': selected}]
				else:
					selected = not has_params or filter_key not in self.params

					# Show all option?
					if getattr(options[filter_key], 'show_all', True):
						self._filter_option_list[filter_key] = [{'query': '?fields={}{}'.format(fields, filter_query, filter_key), 'text': 'All', 'selected': selected}]
					else:
						self._filter_option_list[filter_key] = []

				for option in options[filter_key]:
					option_query_base = '?fields={}{}'.format(fields, filter_query)
					option_query = '{}&{}={}'.format(option_query_base, filter_key, option['val'])
					option_selected = False
					if has_params:
						if self.params.get(filter_key) == option['val']:
							option_query = option_query_base
							option_selected = True
						elif self.filter_current_region and not self.params.get(filter_key):
							# If no region filter is set and we are filtering by current region
							if filter_key == 'site_region' and self.request.get('region').slug == option['val']:
								option_query = option_query_base
								option_selected = True
					self._filter_option_list[filter_key].append({'query': option_query, 'text': option['name'], 'selected': option_selected})

		return self._filter_option_list

	def filter_value_list(self):
		if not hasattr(self, '_filter_value_list'):
			self._filter_value_list = {}
			for fltr in self.filters:
				filter_key = fltr[1]
				if self.params.get(filter_key):
					self._filter_value_list[filter_key] = self.params.get(filter_key)

		return self._filter_value_list

	def filter_notext_value_list(self):
		if not hasattr(self, '_filter_notext_value_list'):
			self._filter_notext_value_list = {}
			for fltr in self.filters:
				filter_key = fltr[1]
				if self.params.get(filter_key) and len(self.filter_option_list()[filter_key]) != 0:
					try:
						self._filter_notext_value_list[filter_key] = self.params.get(filter_key)
					except Exception as ex:
						print(ex)

		return self._filter_notext_value_list

	def filter_options(self):
		raise NotImplementedError('Filter Options must be overridden in child class')


class RegionReport(FilteredReport):

	@staticmethod
	def all_regions():
		shopping_regions = Region.objects.allows_shopping()
		return shopping_regions if shopping_regions else Region.objects.all()

	@staticmethod
	def include_regions():
		return RegionReport.all_regions().count() > 1

	@property
	def filters(self):
		if self.include_regions():
			return [('Region', 'site_region'), ]
		return []

	def filter_options(self):
		if self.include_regions():
			regions = self.all_regions()
			if hasattr(self, 'request') and not self.request.get('user').is_superuser:
				regions = self.request.get('user').regions.all()
			return {'site_region': [{'val': c.slug, 'name': str(c)} for c in regions]}
		return {'site_region': []}

	@property
	def is_region_filtered(self):
		return getattr(self, 'params', {}).get('site_region') != 'all'

	@property
	def filter_to_current_region(self):
		user = getattr(self, 'request', {}).get('user')
		if user and not user.is_superuser or (user.is_superuser and self.filter_current_region):
			return True

	@property
	def filtered_to_regions(self):
		if self.include_regions():
			if self.is_region_filtered:
				return [self.params['site_region']]
			else:
				return [r['val'] for r in self.filter_options()['site_region']]
		return [c.slug for c in self.all_regions()]

	def order_region_filter(self, orders):
		if self.include_regions():
			return orders.filter(region__slug__in=self.filtered_to_regions)
		return orders

	def run(self, *args, **kwargs):
		filters = None
		if self.include_regions() and len(self.filtered_to_regions) != len(self.all_regions()):
			filters = []
			for rgn in self.filtered_to_regions:
				filters.append('ga:dimension1=={}'.format(Region.objects.get(slug=rgn).name))
			if filters:
				if 'filters' in kwargs:
					kwargs['filters'] = '{};{}'.format(kwargs['filters'], ','.join(filters))
				else:
					kwargs['filters'] = ','.join(filters)
		return super(RegionReport, self).run(*args, **kwargs)

	def set_request(self, request):
		super().set_request(request)
		# Set to current region if not region params provided
		if not self.params.get('site_region') and self.filter_to_current_region:
			self.params['site_region'] = self.request.get('region').slug
		elif not self.params.get('site_region'):
			self.params['site_region'] = 'all'


ReportManager.load_from_apps()
