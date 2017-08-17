import datetime
from dateutil.parser import parse

from django import forms
from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.utils import from_current_timezone, to_current_timezone
from django.utils.encoding import smart_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from mptt.forms import TreeNodeChoiceFieldMixin
from sortedm2m import forms as sortedm2m_forms

from .. import widgets
from ..validators import RelativeURLValidator


class UploadField(forms.CharField):
	"Custom field for using the file uploader"
	widget = widgets.Uploader


class DateField(forms.DateField):
	"Custom field to set date picker and parse any date"
	widget = widgets.Date

	def prepare_value(self, value):
		if isinstance(value, datetime.datetime):
			value = to_current_timezone(value).strftime("%Y-%m-%d")
		return value

	def to_python(self, value):
		if value in validators.EMPTY_VALUES:
			return None
		if isinstance(value, datetime.datetime):
			return from_current_timezone(value)
		if isinstance(value, datetime.date):
			result = datetime.datetime(value.year, value.month, value.day)
			return from_current_timezone(result)
		try:
			result = parse(value)
		except (TypeError, ValueError):
			raise ValidationError(self.error_messages['invalid'])
		return from_current_timezone(result)


class DateTimeField(forms.DateTimeField):
	"Custom field to set date time picker and parse any date/time"
	widget = widgets.DateTime

	def prepare_value(self, value):
		if isinstance(value, datetime.datetime):
			value = to_current_timezone(value).strftime("%Y-%m-%dT%H:%M:%S")
		return value

	def to_python(self, value):
		if value in validators.EMPTY_VALUES:
			return None
		if isinstance(value, datetime.datetime):
			return from_current_timezone(value)
		if isinstance(value, datetime.date):
			result = datetime.datetime(value.year, value.month, value.day)
			return from_current_timezone(result)
		try:
			result = parse(value)
		except (TypeError, ValueError):
			raise ValidationError(self.error_messages['invalid'])
		return from_current_timezone(result)


class SortedMultipleChoiceField(sortedm2m_forms.SortedMultipleChoiceField):
	widget = widgets.SortedSelectMultiple


class PermissionChoiceIterator(forms.models.ModelChoiceIterator):
	"""
	This ModelChoiceIterator iterator override adds one extra value to
	each `choice` tuple when passing it on to the widget, so the permissions
	can be grouped and sorted correctly
	"""

	def choice(self, obj):
		return (self.field.prepare_value(obj), self.field.label_from_instance(obj), obj)


class PermissionField(forms.ModelMultipleChoiceField):
	"Custom field for permission selection"
	# widget = widgets.PermissionSelector

	def _get_choices(self):
		return PermissionChoiceIterator(self)

	choices = property(_get_choices, forms.ChoiceField._set_choices)


class RegionChoiceIterator(forms.models.ModelChoiceIterator):
	"""
	This ModelChoiceIterator iterator override adds one extra value to
	each `choice` tuple when passing it on to the widget, so the region
	code can be displayed in the template.
	"""

	def choice(self, obj):
		return (self.field.prepare_value(obj), self.field.label_from_instance(obj), obj.slug)


class RegionField(forms.ModelMultipleChoiceField):
	"Custom field for region selection"
	# widget = widgets.Region

	def __init__(self, *args, **kwargs):
		super(RegionField, self).__init__(*args, **kwargs)
		self._choices = RegionChoiceIterator(self)


class RelativeURLField(forms.URLField):
	widget = forms.widgets.TextInput

	def clean(self, value):
		root = settings.ROOT_URL.replace('https://', 'http://').strip('/')
		ssl_root = root.replace('http://', 'https://')
		if value.startswith(root):
			value = value.replace(root, '')
		elif value.startswith(ssl_root):
			value = value.replace(ssl_root, '')

		try:
			return super().clean(value)
		except ValidationError:
			if value.startswith('/'):
				newvalue = 'https://www.example.com{}'.format(value)
				super().clean(newvalue)
				return value
			raise


class SortableField(forms.CharField):
	"Custom field to set sortable values in inlines"
	widget = widgets.Sortable


class TreeNodeChoiceField(TreeNodeChoiceFieldMixin, forms.ModelChoiceField):
	"Override MPTT TreeNodeChoiceField"

	def label_from_instance(self, obj):
		"""
		Creates labels which represent the tree level of each node when
		generating option labels.
		"""
		level_indicator = self._get_level_indicator(obj)
		name = getattr(obj, 'region_name', obj.name)
		return mark_safe(level_indicator + ' ' + conditional_escape(smart_text(name)))


class TreeNodeMultipleChoiceField(TreeNodeChoiceFieldMixin, forms.ModelMultipleChoiceField):
	"Override MPTT TreeNodeMultipleChoiceField"

	def label_from_instance(self, obj):
		"Creates labels for multiple choice fields with full path context."
		name = getattr(obj, 'region_str', obj.name)
		return mark_safe(conditional_escape(smart_text(name)))
