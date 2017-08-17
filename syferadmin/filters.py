import datetime

from django.contrib import admin
from django.db.models import Q
from django.utils.module_loading import import_string
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _


class DefaultValueFilter(admin.SimpleListFilter):
	"""
	Filter that allows you to set the default selected value.

	This allows you to only show active items by default and the user must
	change the sort to see inactive items.

	See ActiveFilter as an example of how to extend this class.
	"""
	default = 'all'

	def choices(self, cl):
		"Return a generator for the options allowed"
		for lookup, title in self.lookup_choices:
			yield {
				'display': title,
				'query_string': cl.get_query_string({
					self.parameter_name: lookup,
				}, []),
				'selected': self.value() == lookup,
			}

	def get_default(self, choice):
		"Get the default value based on the default property on the class"
		if choice == self.default:
			return None
		return choice

	def is_filtered(self, choice):
		"See if choice is actually filtered against. Use this in queryset()"
		if self.value() == choice:
			return True
		if self.value() is None and choice == self.default:
			return True
		return False


class ActiveFilter(DefaultValueFilter):
	"""
	Filter items by active status

	If you want to set the default filter to show active products only add the
	following property to an extended class:

	default = 'active'
	"""
	parameter_name = 'active'
	title = _('Active')

	def lookups(self, request, model_admin):
		return (
			(self.get_default('all'), _('All')),
			(self.get_default('active'), _('Yes')),
			(self.get_default('inactive'), _('No')),
		)

	def queryset(self, request, queryset):
		if self.is_filtered('inactive'):
			return queryset.exclude(active=True)
		elif self.is_filtered('active'):
			return queryset.exclude(active=False)


class DateRangeFilter(admin.filters.FieldListFilter):
	"""
	Admin filter for date range using the HTML5 Date Input Widget

	Heavily inspired from https://pypi.python.org/pypi/django-daterange-filter
	"""
	template = 'admin/date_range_filter.html'
	filter_prefix = 'drf__'

	def __init__(self, field, request, params, model, model_admin, field_path):
		self.lookup_kwarg_start = '{}__gte'.format(field_path)
		self.lookup_kwarg_end = '{}__lte'.format(field_path)
		super().__init__(field, request, params, model, model_admin, field_path)
		self.form = self.get_form(request)

	def choices(self, cl):
		return []

	def expected_parameters(self):
		return [self.lookup_kwarg_start, self.lookup_kwarg_end]

	def get_form(self, request):
		from syferadmin.forms import DateRangeForm
		return DateRangeForm(request, data=self.used_parameters, field_name=self.field_path)

	def queryset(self, request, queryset):
		if self.form.is_valid():
			# Remove nulls
			param_keys = [self.lookup_kwarg_start, self.lookup_kwarg_end]
			filter_params = dict((k, v) for k, v in self.form.cleaned_data.items() if k in param_keys and v)

			# Optionally filter end date
			if filter_params.get(self.lookup_kwarg_end) is not None:
				filter_params['{}__lt'.format(self.field_path)] = filter_params.pop(self.lookup_kwarg_end) + datetime.timedelta(days=1)

			return queryset.filter(**filter_params)
		else:
			return queryset


class ExpiredFilter(DefaultValueFilter):
	"""
	Filter schedulable items by their expiration status

	See ActiveFilter to see how to change the default filter value
	"""
	parameter_name = 'expired'
	title = _('Expired')

	def lookups(self, request, model_admin):
		return (
			(self.get_default('all'), _('All')),
			(self.get_default('expired'), _('Yes')),
			(self.get_default('current'), _('No')),
		)

	def queryset(self, request, queryset):
		if self.is_filtered('expired'):
			return queryset.filter(end_date__lt=now())
		elif self.is_filtered('current'):
			return queryset.filter(Q(end_date__gte=now()) | Q(end_date=None))


class RegionFilter(admin.SimpleListFilter):
	"Filter objects based on the regions the user has access to"
	parameter_name = 'rgn'
	title = _('Region')

	def lookups(self, request, model_admin):
		if 'regions' not in model_admin.model._meta.get_all_field_names():
			return None
		regions = request.user.regions.parents()
		if request.user.is_superuser:
			from syferadmin.models import Region
			regions = Region.objects.parents()
		if regions.count() > 1:
			return ((region.slug, region.admin_name()) for region in regions.all())

	def queryset(self, request, queryset):
		if self.value() is not None:
			return queryset.filter(regions__slug=self.value())
		return queryset


class RelatedContentFilter(admin.SimpleListFilter):
	"Filter objects based on the content that they have been related to"
	parameter_name = 'relatedto'
	title = _('Used On')

	def lookups(self, request, model_admin):
		from django.contrib.contenttypes.models import ContentType
		from syferadmin.models import Related
		model_type = ContentType.objects.get_for_model(model_admin.model)
		related_types = Related.objects.filter(related_content_type=model_type).order_by('content_type').values_list('content_type', flat=True).distinct()
		for rtype in ContentType.objects.filter(id__in=related_types):
			yield (rtype.id, rtype.model_class().__name__)

	def queryset(self, request, queryset):
		if self.value() is not None:
			from django.contrib.contenttypes.models import ContentType
			from syferadmin.models import Related
			model_type = ContentType.objects.get_for_model(queryset.model)
			related_type = ContentType.objects.get_for_id(self.value())
			items = Related.objects.filter(related_content_type=model_type, content_type=related_type).order_by('related_object_id').values_list('related_object_id', flat=True).distinct()
			return queryset.filter(pk__in=items)
		return queryset
