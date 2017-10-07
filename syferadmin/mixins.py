from functools import partial, reduce
import json
import re
from textwrap import wrap
import warnings
import operator

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.utils import unquote, lookup_needs_distinct
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.admin import GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.contrib.messages import error, success
from django.core.exceptions import PermissionDenied, ImproperlyConfigured, SuspiciousOperation, ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.apps import apps
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.db.utils import ProgrammingError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import date
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime, now
from django.utils.translation import ugettext_lazy as _
try:
	from django.utils.module_loading import import_string
except ImportError:
	from django.utils.module_loading import import_by_path as import_string

from imagekit.models.fields.utils import ImageSpecFileDescriptor
from imagekit.cachefiles import ImageCacheFile
from imagekit.registry import generator_registry
from jsonfield import JSONField

from .decorators import cacheable, memoize
from .middleware.threadlocal import get_request
from .fields.model_fields import RegionField
from .filters import RegionFilter
from .utils import current_region, human_join


class ActionsAdmin(object):

	def __init__(self, *args, **kwargs):
		self.list_display = self.list_display + ('list_actions',)
		super(ActionsAdmin, self).__init__(*args, **kwargs)

	def action_checkbox(self, obj):
		"""Override from https://github.com/django/django/blob/17557d068c43bd61cdc6c18caf250ffa469414a1/django/contrib/admin/options.py#L822
		to add an empty label to the checkbox"""
		checkbox_id = 'action_select_{}'.format(obj.pk)
		checkbox = helpers.checkbox.render(helpers.ACTION_CHECKBOX_NAME, force_text(obj.pk), attrs={'id': checkbox_id})
		return '{}{}'.format(checkbox, "<label for={}></label>".format(checkbox_id))
	action_checkbox.short_description = mark_safe('<input type="checkbox" id="action-toggle" /><label for="action-toggle"></label>')
	action_checkbox.allow_tags = True

	def get_list_actions(self, obj):
		actions = []
		request = get_request()
		label, name = (obj._meta.app_label, obj._meta.model_name,)
		url_scheme = 'admin:{}_{}_{}'
		if self.has_change_permission(request, obj):
			actions.append(('Edit', 'edit', reverse(url_scheme.format(label, name, 'change'), args=[obj.id])),)
		if self.has_delete_permission(request, obj) and (
			not hasattr(self, 'can_delete') or self.can_delete):
			actions.append(('Delete', 'delete', reverse(url_scheme.format(label, name, 'delete'), args=[obj.id])))
		return actions

	def list_actions(self, obj):
		actions = ['<a href="{2}" class="{1}" title="{3}">{0}</a>'.format(
			a[0], a[1], a[2], (a[3] if len(a) > 3 else a[0])) for a in self.get_list_actions(obj)]
		return """
				<div class="actions">
					<ul>{0}</ul>
				</div>
				""".format('<li>' + '</li><li>'.join(actions) + '</li>')
	list_actions.allow_tags = True
	list_actions.short_description = 'Actions'
	list_actions.row_classes = 'actions'


class ActivatableAdmin(object):

	def activation_url(self):
		return "admin:{}_{}_activate".format(*self.model_info)

	@property
	def model_info(self):
		return self.model._meta.app_label, self.model._meta.model_name

	def get_urls(self):
		urls = [
			url(r'^(.+)/activate/$', self.admin_site.admin_view(self.activate),
				name='{}_{}_activate'.format(*self.model_info)),
		]
		return urls + super(ActivatableAdmin, self).get_urls()

	def activate(self, request, object_id):
		return_url = request.META.get("HTTP_REFERER", "admin:{}_{}_changelist".format(*self.model_info))
		obj = get_object_or_404(self.model, pk=unquote(object_id))
		if not self.has_change_permission(request, obj):
			error(request, "Sorry, you can't do that")
			return redirect(return_url)
		obj.active = not obj.active
		obj.save()
		return redirect(return_url)


class AlignmentMixin(models.Model):
	TOP_LEFT = 'top left'
	TOP_CENTER = 'top center'
	TOP_RIGHT = 'top right'
	MIDDLE_LEFT = 'middle left'
	MIDDLE_CENTER = 'middle center'
	MIDDLE_RIGHT = 'middle right'
	BOTTOM_LEFT = 'bottom left'
	BOTTOM_CENTER = 'bottom center'
	BOTTOM_RIGHT = 'bottom right'
	ALIGNMENTS = (
		(TOP_LEFT, 'Top Left'),
		(TOP_CENTER, 'Top Center'),
		(TOP_RIGHT, 'Top Right'),
		(MIDDLE_LEFT, 'Middle Left'),
		(MIDDLE_CENTER, 'Middle Center'),
		(MIDDLE_RIGHT, 'Middle Right'),
		(BOTTOM_LEFT, 'Bottom Left'),
		(BOTTOM_CENTER, 'Bottom Center'),
		(BOTTOM_RIGHT, 'Bottom Right'),
	)
	alignment = models.CharField(max_length=20, choices=ALIGNMENTS, blank=True, null=True)

	class Meta:
		abstract = True


class ExtraInlinesAdmin(object):

	def __init__(self, *args, **kwargs):
		super(ExtraInlinesAdmin, self).__init__(*args, **kwargs)
		if hasattr(self, 'extra_inlines'):
			for inline in self.extra_inlines:
				cls = import_string(inline)
				if cls not in self.inlines:
					self.inlines.append(cls)


class ExtraActionsAdmin(object):

	def __init__(self, *args, **kwargs):
		super(ExtraActionsAdmin, self).__init__(*args, **kwargs)
		if hasattr(self, 'extra_actions'):
			for action in self.extra_actions:
				cls = import_string(action)
				if cls not in self.actions:
					self.actions.append(cls)


class TextAlignmentMixin(models.Model):
	TEXT_LEFT = 'text-left'
	TEXT_CENTER = 'text-center'
	TEXT_RIGHT = 'text-right'
	TEXT_ALIGNMENTS = (
		(TEXT_LEFT, 'Left Aligned'),
		(TEXT_CENTER, 'Center Aligned'),
		(TEXT_RIGHT, 'Right Aligned'),
	)
	text_alignment = models.CharField(max_length=20, choices=TEXT_ALIGNMENTS, blank=True, null=True)

	class Meta:
		abstract = True


class StyleMixin(models.Model):
	DARK = 'dark'
	LIGHT = 'light'
	STYLES = (
		(DARK, 'Dark Text on Light Background'),
		(LIGHT, 'Light Text on Dark Background'),
	)
	style = models.CharField(max_length=10, choices=STYLES, blank=True, null=True)

	class Meta:
		abstract = True


class DisabledFieldsMixin(object):
	"""
	ModelForm Mixin that disables a list of fields for a model form.

	Fields will be in disabled state and will be cleaned to the original value
	upon form submission. It is assumed the fields will be valid initially.

	Example:
		class MyModelForm(DisabledFieldsMixin, ModelForm):
			DISABLED_FIELDS = ['name', 'url', ]
			...
	"""
	DISABLED_FIELDS = []

	def __init__(self, *args, **kwargs):
		super(DisabledFieldsMixin, self).__init__(*args, **kwargs)
		instance = getattr(self, 'instance', None)
		if instance and instance.pk and self.DISABLED_FIELDS:
			for field in self.DISABLED_FIELDS:
				# Disable field
				self.fields[field].widget.attrs['readonly'] = True

				# Set a clean method that returns the current value
				# in case there are some shysters out there
				def clean_field(field):
					return getattr(instance, field, None)
				setattr(self, 'clean_{0}'.format(field), partial(clean_field, field))


class Fieldset:
	"Used in conjuction with FieldsetForm to provide fieldsets to a regular form"

	def __init__(self, title, fields, description=None, classes=None):
		self.title = title
		self.fields = fields
		self.description = description
		self.classes = classes

	def __iter__(self):
		for field in self.fields:
			yield field


class FieldsetForm:
	"""
	Allow a regular form to have Meta.fieldsets. It matches the signature of'
	Admin.fieldsets and should be placed in the forms Meta class
	"""
	ValidationError = ValidationError

	class Meta:
		pass

	def fieldsets(self):
		meta = getattr(self, '_meta', None)
		if not meta:
			meta = getattr(self, 'Meta', None)

		if not meta or not meta.fieldsets:
			return

		for fieldset in meta.fieldsets:
			yield Fieldset(
				title=fieldset[0],
				description=fieldset[1].get('description', None),
				classes=fieldset[1].get('classes', None),
				fields=(self[f] for f in fieldset[1].get('fields', []))
			)


class ImageResizable(object):

	def resized(self, source='image', id='imagekit:thumbnail',
		dest=None, **kwargs):
		"""
		Return a resized image for source. You can resize it a few different ways
		1. Pass an id from your imagespecs.py file (Ex: sideteam:member.thumb)
		2. Set a width= and/or height= to crop the image to that size
		3. Set a width= and/or height= and crop=0 to resize within the
			width/height bounds

		If you supply a dest then the object.dest property will be set with the image

		Available arguments:
			width=int
			height=int
			crop=0|1
			format='JPEG|PNG|GIF'
			options={'quality':'0-100'}
		"""

		if dest and hasattr(self, dest):
			return getattr(self, dest)

		kwargs['source'] = getattr(self, source)

		generator = generator_registry.get(id, **kwargs)
		image = ImageCacheFile(generator)
		if dest:
			setattr(self, dest, image)
		return image


class ImageContainer(ImageResizable):

	def regenerate(self):
		images = [name for name, field in self.__class__.__dict__.items()
					if type(field) is ImageSpecFileDescriptor]
		[getattr(self, image_name).generate(True) for image_name in images]

	def _img(self, field='image'):
		img = getattr(self, field)
		if img:
			return """<img src="{0}" />""".format(img.url)


class MetaFormSet(BaseGenericInlineFormSet):
	"""
	Mixin for defining fields in meta inline. Use with `MetaInline` mixin.

	Example for meta_keys:
		meta_keys = (('my_field_key', 'My Field Title'), ('another_arbitrary_field', 'Arbitrary Title'),)
	"""
	meta_keys = None

	def _construct_form(self, i, **kwargs):
		"Construct dynamic form from meta_keys"
		from syferadmin.models import Meta
		if not self.meta_keys:
			raise ImproperlyConfigured('You must set meta_keys to use {} mixin'.format(self.__class__.__name__))
		meta_key = self.meta_keys[i]
		try:
			kwargs['instance'] = self.get_queryset().get(key=meta_key[0])
		except Meta.DoesNotExist:
			kwargs['instance'] = Meta(key=meta_key[0], content_object=self.instance)
			kwargs['instance'].save()
		form = super(MetaFormSet, self)._construct_form(i, **kwargs)
		form.fields['id'].initial = kwargs['instance'].pk
		form.fields['id'].value = kwargs['instance'].pk
		form.fields['key'].initial = meta_key[0]

		if 'modeltranslation' in settings.INSTALLED_APPS and Meta.languages() and hasattr(self, 'translation_form'):
			for l in Meta.languages():
				field = form.fields['{}_{}'.format('value', l[0].replace('-', '_'))]

				field.required = False

				if settings.MODELTRANSLATION_DEFAULT_LANGUAGE and l[0] == settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
					field.default_field = True
					field.label = meta_key[1]
				else:
					field.label = '{} [{}]'.format(meta_key[1], l[1])
					# Setting custom attr to know wether or not we are dealing with a translatable field in the frontend
				field.translateable = True
		else:
			form.fields['value'].label = meta_key[1]
			form.fields['value'].required = False

			# Hide the translation fields from non translated metas
			if 'modeltranslation' in settings.INSTALLED_APPS:
				for l in Meta.languages():
					try:
						field = form.fields['{}_{}'.format('value', l[0].replace('-', '_'))]
						field.hide_translation = True
					except KeyError:
						pass

		if len(meta_key) >= 3:
			for field in meta_key[2]:
				setattr(form.fields['value'], field, meta_key[2][field])
		return form


class MetaInline(GenericStackedInline):
	"""
	Mixin for grouping meta fields into an inline form. Use with `MetaFormSet` mixin.

	Be sure to set `model` attr to the `Meta` model when using this mixin.
	Django needs the model defined before instantiation.
	"""
	formset = MetaFormSet
	template = 'meta/admin_meta_inline.html'

	class Media:
		css = {'all': ('syferadmin/css/meta-inline.css',)}
		js = ('syferadmin/js/meta-inline.js',)

	def __init__(self, parent_model, admin_site):
		"Get fields from formset and set some thing Django expects in inline forms"
		from .forms import MetaForm
		if not isinstance(self.form, MetaForm):
			self.form = MetaForm

		# Get meta keys defined in Formset
		self.meta_keys = [key for key in self.formset.meta_keys]

		# Force the inline counts to the amount of
		# custome meta keys
		self.extra = self.min_num = self.max_num = len(self.meta_keys)
		super(MetaInline, self).__init__(parent_model, admin_site)

	def get_queryset(self, request):
		"Change the queryset to only return keys defined in formset"
		queryset = super(MetaInline, self).get_queryset(request)
		return queryset.filter(key__in=[key[0] for key in self.meta_keys])


class MetaModel(models.Model):
	"""
	Mixin for working with generic key/value store for models.
	"""
	meta_set = GenericRelation('syferadmin.Meta')

	class Meta:
		abstract = True

	@cached_property
	def _all_meta(self):
		"""Cache all meta by key"""
		return {meta.key: self.type_cast(meta.value) for meta in self.meta_set.all()}

	def _clear_cached_meta(self):
		if hasattr(self, '_all_meta'):
			delattr(self, '_all_meta')

	@staticmethod
	def type_cast(value):
		"""
		Try to convert value to a primitive type

		Only supports bool values right now, but can easily be extended.
		"""
		bool_values = {'True': True, 'False': False}
		if value in bool_values:
			return bool_values[value]

		return value

	def meta(self, *args):
		if len(args) > 1:
			return self.meta_save(*args)
		if len(args):
			return self.meta().get(args[0], None)
		return self._all_meta

	def meta_wildcard(self, search):
		metas = self.meta()
		if search.startswith('^'):
			return {v: metas[v] for v in metas if v.startswith(search[1:])}
		if search.endswith('$'):
			return {v: metas[v] for v in metas if v.endswith(search[:-1])}
		return {v: metas[v] for v in metas if search in v}

	def meta_remove(self, key):
		try:
			self.meta_set.get(key=key).delete()
		except self.meta_set.model.DoesNotExist:
			pass
		self._clear_cached_meta()

	def meta_save(self, key, value, *args):
		if value is None:
			return self.meta_remove(key)
		try:
			meta = self.meta_set.get(key=key)
		except self.meta_set.model.DoesNotExist:
			self.meta_set.create(key=key, value=value)
		else:
			meta.value = value
			if 'modeltranslation' in settings.INSTALLED_APPS and len(args) > 0 and args[0]:
				from syferadmin.models import Meta
				if Meta.languages() and settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
					setattr(meta, '{}_{}'.format('value', settings.MODELTRANSLATION_DEFAULT_LANGUAGE.replace('-', '_')), value)
			meta.save()
		self._clear_cached_meta()


class RuleAdmin(admin.ModelAdmin):
	"Base rule admin class for creating conditions/effects/etc."
	change_form_template = 'admin/admin_rule_edit.html'


class RuleInline(admin.StackedInline):
	template = 'admin/admin_rule_builder.html'
	extra = 0

	def types(self):
		return sorted([(key, value) for key, value in self.model.types().items()], key=lambda x: x[1].sort if hasattr(x[1], 'sort') else 99999)


class ThumbAdmin(admin.ModelAdmin):

	def change_display(self, obj, html):
		request = get_request()
		label, name = (obj._meta.app_label, obj._meta.model_name,)
		if not self.has_change_permission(request, obj):
			return html
		return '<a href="{}">{}</a>'.format(reverse('admin:{}_{}_change'.format(label, name), args=[obj.id]), html)

	def thumb_display(self, obj):
		thumb = """<div class="thumb"><img src="{}" /></div>"""
		return self.change_display(obj, thumb)


class RegionalAdmin(ThumbAdmin):
	"""
	All regional model admins should inherit this mixin
	"""

	def __init__(self, model, *args, **kwargs):
		"Add regions field and changelist display if there are multiple regions"
		from .models import Region
		try:
			if not hasattr(self, 'regions_enabled'):
				self.regions_enabled = (hasattr(model, 'region') or hasattr(model, 'regions')) and Region.objects.multiple()
		except ProgrammingError:
			pass
		else:
			if self.regions_enabled:
				if self.fieldsets and 'regions' in [field.name for field in model._meta.get_fields()]:
					fields = self.fieldsets[0][1]['fields']
					if 'regions' not in fields:
						self.fieldsets[0][1]['fields'] = tuple(fields) + ('regions',)
				if self.list_display and 'region_display' not in self.list_display:
					self.list_display = tuple(self.list_display) + ('region_display',)
				if self.search_fields and RegionFilter not in self.list_filter:
					self.list_filter = tuple(self.list_filter) + (RegionFilter,)
		super(RegionalAdmin, self).__init__(model, *args, **kwargs)

	@staticmethod
	def has_region_permission(request, obj=None):
		if request.user.is_superuser:
			return True
		if obj:
			user_regions = request.user.regions.all()
			if hasattr(obj, 'region'):
				if obj.region not in user_regions:
					return False
			else:
				for region in obj.regions.parents():
					if region not in user_regions:
						return False
		return True

	def formfield_for_manytomany(self, db_field, request, **kwargs):
		"Filter available regions for current user"
		if db_field.name == 'regions':
			from .models import Region
			kwargs['queryset'] = request.user.regions.parents() if not request.user.is_superuser else Region.objects.parents()
		return super(RegionalAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

	def get_list_display(self, request):
		if not request.user.has_all_regions and not request.user.is_superuser:
			if 'active' in self.list_display:
				list_display = list(self.list_display)
				list_display.remove('active')
				return list_display
		return self.list_display

	def get_list_display_links(self, request, list_display):
		return (None, )

	def get_queryset(self, request):
		queryset = super(RegionalAdmin, self).get_queryset(request)
		if request.user.is_superuser:
			return queryset
		if hasattr(queryset.model, 'region'):
			return queryset.filter(region__in=request.user.regions.all())
		else:
			return queryset

	def get_urls(self):
		info = self.model._meta.app_label, self.model._meta.model_name
		urls = [
			url(r'^(\d+)/(\d+)/region_disable/$', self.admin_site.admin_view(self.region_disable),
				name='{}_{}_region_disable'.format(*info)),
			url(r'^(\d+)/(\d+)/region_enable/$', self.admin_site.admin_view(self.region_enable),
				name='{}_{}_region_enable'.format(*info)),
		]
		return urls + super(RegionalAdmin, self).get_urls()

	def has_delete_permission(self, request, obj=None):
		if not self.has_region_permission(request, obj):
			return False
		return super(RegionalAdmin, self).has_delete_permission(request, obj)

	def has_change_permission(self, request, obj=None):
		if not self.has_region_permission(request, obj):
			return False
		return super(RegionalAdmin, self).has_change_permission(request, obj)

	def region_disable(self, request, object_id, region_id):
		return self.region_toggle(request, object_id, region_id, 'remove')

	def region_display(self, obj):
		"Display region icons with region toggle links where permissible"
		regions = []
		if hasattr(obj, 'region'):
			regions.append('<li class="region {0} active"><a title="{1}">{1}</a></li>'.format(obj.region.slug, obj.region.name))
		else:
			from .models import Region
			request = get_request()
			label, name = (obj._meta.app_label, obj._meta.model_name,)
			active_regions = obj.regions.parents()

			for region in Region.objects.parents():
				classes = region.slug
				action = 'Enable'
				if region in active_regions:
					action = 'Disable'
					classes += ' active'

				# Link if allowed to toggle
				if request.user.is_superuser or region in request.user.regions.parents():
					content = '<a href="{}">{}</a>'.format(reverse('admin:{}_{}_region_{}'.format(label, name, action.lower()), args=[obj.pk, region.pk]), region.name)
				else:
					content = '<a>{}</a>'.format(region.name)

				regions.append('<li class="region {}">{}</li>'.format(classes, content))

		return '<ul class="regions">{}</ul>'.format(''.join(regions))
	region_display.short_description = 'Regions'
	region_display.allow_tags = True

	def region_enable(self, request, object_id, region_id):
		return self.region_toggle(request, object_id, region_id)

	def region_toggle(self, request, object_id, region_id, action='add'):
		"Toggle object association to region"
		from .models import Region
		obj = get_object_or_404(self.model, pk=unquote(object_id))
		region = request.user.regions.get(pk=unquote(region_id)) if not request.user.is_superuser else Region.objects.parents().get(pk=unquote(region_id))
		if region:
			try:
				# If there is already a obj with this slug in this region add error message and skip the save
				if not region.verify_unique_by_region(cleaned_data=None, obj=obj):
					error(request, '{} with url "{}" already exists for region {}'.format(obj.__class__.__name__, obj.slug, region))
				else:
					getattr(obj.regions, action)(region)
					obj.save()
					response = 'Added {} to {}' if action == 'add' else 'Removed {} from {}'
					success(request, response.format(obj, region.admin_name()))
			except PermissionDenied as exception:
				error(request, exception)
		return redirect(request.META.get('HTTP_REFERER', None))


class RegionalQuerySet(QuerySet):

	def active(self, *args, **kwargs):
		warnings.warn("Please use public() instead of active()", DeprecationWarning, stacklevel=2)
		return self.public(*args, **kwargs)

	def for_region(self, region=None):
		if not region:
			region = self.get_region()
		if hasattr(self.model, 'region'):
			return self.filter(region=region)
		else:
			return self.filter(regions=region)

	def get_region(self):
		return current_region()

	def public(self, region=None):
		return self.for_region(region).filter(active=True)


class RegionalManager(models.Manager):

	def active(self, *args, **kwargs):
		warnings.warn("Please use public() instead of active()", DeprecationWarning, stacklevel=2)
		return self.public(*args, **kwargs)

	def for_region(self, region=None):
		return self.get_queryset().for_region(region)

	def get_queryset(self):
		return RegionalQuerySet(self.model)

	def public(self, region=None):
		return self.get_queryset().public(region)


class RegionalModel(models.Model):
	"""
	All regional models should inherit this mixin
	"""
	regions = RegionField(blank=True, related_name='%(app_label)s_%(class)s_related')

	class Meta:
		abstract = True

	@property
	def region_name(self):
		if self.region_human_list:
			return '{} ({})'.format(self.name, self.region_human_list)
		return self.name

	@property
	def region_str(self):
		if self.region_human_list:
			return '{} ({})'.format(self, self.region_human_list)
		return str(self)

	@property
	@cacheable
	def region_human_list(self):
		from .models import Region
		if Region.objects.multiple():
			regions = [r.slug.upper() for r in self.regions.parents()]
			if len(regions) == Region.objects.parents().count():
				regions = 'All Regions'
			else:
				regions = human_join(regions)
			return regions

	@cacheable
	def region_display(self):
		from .models import Region
		if Region.objects.multiple() and self.regions.parents():
			regions = "".join(['<li class="region {} active"><a>{}</a></li>'.format(r.slug, r.name) for r in self.regions.parents()])
			return '<ul class="regions">{}</ul>'.format(regions)
		return ''


def add_to_default_region(sender, **kwargs):
	from .models import Region

	instance = kwargs['instance']
	model = type(instance)

	if not issubclass(model, RegionalModel):
		return

	if instance and Region.objects.parents().count() == 1:
		instance.regions.add(Region.objects.first())

post_save.connect(add_to_default_region)


class RelatableModel(object):
	"""
	Mixin for relatable models. Use with admin.RelatedInline to create
	content buckets for each related content_type.

	Example:
		class MyModel(models.Model, RelatableModel):
			related_models = (('post', 'sidepost.post'))

		class Post(models.Model, RelatableModel)
			related_models = []

		MyModel().related('post')  # Get related posts for this model

		Post().related_to('products.product')  # Get products related to this post
	"""
	related_models = []
	# Override related_models on a per-instance basis based on slug or pk
	# Experimental feature which we can remove if it's not used or too hacky.
	related_overrides = {}

	@staticmethod
	def prefetch_relations(relations, fields):
		"""
		Cache each relation association on the relation
		instead of executing one query for each lookup.

		:param relations: queryset/list of Related objects
		:param fields: Dict of fields containing `object_id` and `content_type_id`
		"""

		# Create dict with content_type_id keys containing dict of pk's of that content type's objects
		content_objects = {}
		for relation in relations:
			content_objects.setdefault(getattr(relation, fields['content_type_id']), set()).add(getattr(relation, fields['object_id']))

		# Grab the distinct content types
		content_types = ContentType.objects.in_bulk(content_objects.keys())

		# Do queries for each content type and store results
		relation_cache = {}
		for content_type, fk_list in content_objects.items():
			ct_model = content_types[content_type].model_class()
			relation_cache[content_type] = ct_model.objects.public().in_bulk(list(fk_list))

		# Cache each result on django's internal cache for the Relation object
		for relation in relations:
			try:
				setattr(relation, '_content_object_cache', relation_cache[getattr(relation, fields['content_type_id'])][getattr(relation, fields['object_id'])])
			except KeyError:
				pass

	def admin_url(self, action='changelist'):
		args = ()
		if action != 'changelist':
			args = (self.pk,)
		return reverse('admin:{}_{}_{}'.format(self._meta.app_label, self._meta.model_name, action), args=args)

	def admin_change(self):
		return self.admin_url('change')

	def delete_related_orphans(self):
		"Delete related orphans for this model"
		from .models import Related
		content_type = ContentType.objects.get_for_model(self.__class__)
		for item in Related.objects.filter(content_type=content_type, object_id=self.pk):
			if not item.related_content_object:
				item.delete()

	def get_related_models(self):
		"""
		Get a list of related models for use in the admin
		"""
		models = []
		if not self.related_models:
			return models

		for model in self.related_overrides.get(self.related_override_key(), self.related_models):
			try:
				group, model_path, extra_fields = model
			except ValueError:
				group, model_path = model
				extra_fields = ()
			app_label, model_name = model_path.split('.')
			models.append((group, apps.get_model(app_label, model_name,), extra_fields, group.replace('_', ' ')))

		return models

	@memoize
	def related(self, name=None, reverse_lookup=False):
		"""
		Find related objects for this model

		:param name: Related model name (dot-notation or related_models alias) or list of names
		:param reverse: Look up related models by reverse relationship
		"""
		if not name and reverse:
			from .models import Related
			model = self
			if hasattr(self, 'parent_model'):
				model = self.parent_model
			ct = ContentType.objects.get_for_model(model)
			ret = Related.objects.filter(related_content_type=ct.pk, related_object_id=self.pk).order_by('content_type__model', 'object_id')
			return ret

		if not name:
			raise Exception('Need a related item name to lookup!')

		# Convert to list if needed
		if isinstance(name, str):
			name = [name]

		# Grab this model's content type
		content_type = ContentType.objects.get_for_model(type(self))

		# Grab model paths via aliases and combine with dot-notation model names
		model_paths = [v[1] for v in self.related_overrides.get(self.related_override_key(), self.related_models) if v[0] in name] + [v for v in name if '.' in v]
		# Grab related content types
		related_content_types = [ContentType.objects.get_for_model(apps.get_model(*model_path.split('.'))) for model_path in model_paths]

		# Set to/from fields
		fields = ['object_id', 'content_type', 'content_object', 'content_type_id']
		_from = dict(zip(fields, fields))
		_to = {k: 'related_{}'.format(v) for (k, v) in _from.items()}

		# Switch to/from if reversed
		if reverse_lookup:
			_from, _to = _to, _from

		args = {
			_from['content_type']: content_type,
			_from['object_id']: self.pk,
			'{}__in'.format(_to['content_type']): related_content_types,
		}

		if not reverse_lookup:
			args['group__in'] = name

		# Get relations
		from .models import Related
		relations = Related.objects.filter(**args)

		# For reverse lookup, if there's only one related content type, query those models directly
		if reverse_lookup and len(related_content_types) == 1:
			return related_content_types[0].model_class().objects.filter(pk__in=relations.values('object_id')).public()
		# Otherwise, prefetch in bulk and cache each content type separately
		else:
			self.prefetch_relations(relations, _to)
			return [getattr(relation, '_content_object_cache') for relation in relations if hasattr(relation, '_content_object_cache')]

	def related_to(self, name=None):
		"""
		Find objects related to this model
		"""
		return self.related(name, True)

	def related_override_key(self):
		# First try to do a regex match against slug
		key = getattr(self, 'slug', getattr(self, 'pk'))
		for _key in self.related_overrides.keys():
			if re.match(_key, key):
				key = _key
		return key

	def related_update(self, name, items, field='id'):
		"""
		Update a list of related items to a group

		Args:
			name (str): Related group name
			items (list): List of related values
			field (str): Field for looking up list of objects
		"""

		# Grab this model's content type
		content_type = ContentType.objects.get_for_model(type(self))

		for group, model, extra, title in self.get_related_models():
			if name == group:
				from .models import Related
				args = {
					'group': name,
					'content_type': content_type,
					'object_id': self.id,
					'related_content_type': ContentType.objects.get_for_model(model),
				}

				# Remove current group relations
				Related.objects.filter(**args).delete()

				# Add new relations
				for i, item in enumerate(items):
					try:
						item_id = item if field == 'id' else model.objects.get(**{field: item}).id
						args.update({
							'sort': i,
							'related_object_id': item_id,
						})
						Related.objects.create(**args)
					except model.DoesNotExist:
						pass

	def relation(self, related=None, group=None):
		"""
		Find Related instance for object and related object
		"""
		if not related:
			return None

		# Try to get parent model for multi-table models
		if hasattr(related, 'parent_model'):
			related_content_type = ContentType.objects.get_for_model(related.parent_model)
		else:
			related_content_type = ContentType.objects.get_for_model(type(related))

		args = {
			'content_type': ContentType.objects.get_for_model(type(self)),
			'object_id': self.pk,
			'related_object_id': related.pk,
			'related_content_type': related_content_type,
		}

		if group:
			args.update({'group': group})

		from .models import Related
		return Related.objects.get(**args)


class SchedulableAdmin(object):

	def schedule(self, obj):
		message = None
		if obj.start_date and now() < obj.start_date:
			return u'<span title="Starts {0}">Starts on {1}</span>'.format(naturaltime(obj.start_date), date(localtime(obj.start_date), 'DATETIME_FORMAT'))
		elif obj.end_date and now() > obj.end_date:
			return u'<span title="Ended {0}">Ended on {1}</span>'.format(naturaltime(obj.end_date), date(localtime(obj.end_date), 'DATETIME_FORMAT'))
		elif obj.end_date and now() < obj.end_date:
			message = u'Ends on {0}'.format(date(localtime(obj.end_date), 'DATETIME_FORMAT'))
			if not obj.start_date:
				return u'<span title="Ends {0}">{1}</span>'.format(naturaltime(obj.end_date), message)
			else:
				return u'<span title="Ends {0}\nStarted {1}">{2}<span class="progress" data-progress="{3}%"><span style="width: {3}%"></span></span></span>'.format(naturaltime(obj.end_date), naturaltime(obj.start_date), message, int(obj.elapsed() * 100))
	schedule.allow_tags = True
	schedule.short_description = 'Schedule'


class SchedulableQuerySet(QuerySet):

	def active(self, *args, **kwargs):
		warnings.warn("Please use public() instead of active()", DeprecationWarning, stacklevel=2)
		return self.public(*args, **kwargs)

	def public(self):
		'Get active records'
		return self.filter(active=True).filter(
			models.Q(start_date__lte=now()) | models.Q(start_date__isnull=True)
		).filter(
			models.Q(end_date__gte=now()) | models.Q(end_date__isnull=True)
		)


class SchedulableManager(models.Manager):

	def active(self, *args, **kwargs):
		warnings.warn("Please use public() instead of active()", DeprecationWarning, stacklevel=2)
		return self.public(*args, **kwargs)

	def public(self):
		return self.get_queryset().public()


class SchedulableModel(models.Model):
	start_date = models.DateTimeField(null=True, blank=True, help_text=_("Hide this content until this date (optional)"))
	end_date = models.DateTimeField(null=True, blank=True, help_text=_("Hide this content after this date (optional)"))

	class Meta:
		abstract = True

	def elapsed(self):
		"Fraction of time elapsed by start/end dates"
		if self.end_date and self.end_date < now():
			return 1
		if not self.start_date or not self.end_date:
			return 0
		if now() < self.start_date:
			return 0
		return (now() - self.start_date).total_seconds() / (self.end_date - self.start_date).total_seconds()

	@property
	def related_admin_extra_data(self):
		return {
			'start_date': self.start_date,
			'end_date': self.end_date,
		}


class SortableAdmin(object):
	sortable = 'flat'
	change_list_template = 'admin/change_list_sortable.html'

	class Media:
		js = ('syferadmin/libs/jquery.mjs.nestedSortable.js',
				'syferadmin/js/sortable.js')

	def __init__(self, *args, **kwargs):
		super(SortableAdmin, self).__init__(*args, **kwargs)
		if hasattr(self.model, 'parent'):
			self.sortable = 'nested'
		# Set this so we can clear out sorts and reset them when items are filtered
		self.original_sortable = self.sortable

	def changelist_view(self, request):
		self.sortable = self.original_sortable
		if any(request.GET.values()):
			self.sortable = False
		return super().changelist_view(request)

	def get_urls(self):
		info = self.model._meta.app_label, self.model._meta.model_name
		urls = patterns('',
			url(r'^sort/$', self.admin_site.admin_view(self.sort),
				name='%s_%s_sort' % info),
		)
		return urls + super(SortableAdmin, self).get_urls()

	def save_model(self, request, obj, form, change):
		"Add a default sort as max(sort) + 1"
		if not obj.pk and obj.sort is None:
			maxval = type(obj).objects.all().aggregate(models.Max('sort'))
			obj.sort = maxval['sort__max'] + 1 if maxval['sort__max'] else 1
		return super(SortableAdmin, self).save_model(request, obj, form, change)

	def sort(self, request):
		result = {'success': False}
		if 'json' in request.POST:
			for i, item_data in enumerate(json.loads(request.POST['json'])):
				if not item_data['item_id']:
					continue
				item = self.model.objects.get(id=item_data['item_id'])
				item.sort = i
				item.parent_id = item_data['parent_id']
				if item_data['parent_id']:
					item.parent = self.model.objects.get(id=item_data['parent_id'])
				else:
					item.parent = None
				item.save()
			if self.sortable == 'nested':
				self.model.objects.rebuild()
			result['success'] = 'Sorting Saved!'
		return HttpResponse(json.dumps(result))


class SortableModel(models.Model):
	sort = models.SmallIntegerField(null=True, blank=True)

	class Meta:
		abstract = True
		ordering = ['sort']

	def adjacent(self, direction='next'):
		if direction not in ('next', 'previous'):
			raise ValueError("Invalid direction '%s' !" % direction)
		# Right now ignoring models without sort set
		if not self.sort:
			return None
		direction = 'gt' if direction == 'next' else 'lt'
		sort_direction = '-' if direction == 'lt' else ''
		try:
			model_set = self.__class__.objects.public().filter(**{'sort__{}'.format(direction): self.sort})
			return model_set.order_by('{}sort'.format(sort_direction)).first()
		except self.DoesNotExist:
			return None

	def next(self):
		return self.adjacent()

	def prev(self):
		return self.adjacent('previous')


class RuleModel(SortableModel):
	type = models.CharField(max_length=50)
	vars = JSONField()

	class Meta:
		abstract = True

	@classmethod
	def meta(cls):
		return cls._meta

	@classmethod
	def types(cls):
		return {x.name(): x for x in cls.__subclasses__() if hasattr(x, 'Meta')}

	def __init__(self, *args, **kwargs):
		"Automatically cast to correct subclass based on type"
		super(RuleModel, self).__init__(*args, **kwargs)
		try:
			subclass = self.types()[self.type]
			self.__class__ = subclass
			if '__init__' in subclass.__dict__:
				self.__init__(*args, **kwargs)
		except KeyError:
			pass

	def __getattr__(self, name):
		if name in self.vars:
			return self.vars[name]
		try:
			return getattr(super(RuleModel, self), name)
		except AttributeError:
			raise AttributeError('`{}` not implemented for type `{}`'.format(name, self.type))


class TrackableModel(models.Model):
	created = models.DateTimeField(default=now, editable=False)
	modified = models.DateTimeField(editable=False)

	class Meta:
		abstract = True

	def save(self, *args, **kwargs):
		self.modified = kwargs.pop('modified', now())
		return super(TrackableModel, self).save(*args, **kwargs)


class AddressModel(TrackableModel, MetaModel):
	address = models.CharField(max_length=150)
	address2 = models.CharField(max_length=75, blank=True, null=True)
	city = models.CharField(_('City'), max_length=70)
	locality = models.CharField(max_length=50, blank=True, null=True)
	country_code = models.CharField(max_length=2)
	postal_code = models.CharField(max_length=20, blank=True, null=True)
	phone = models.CharField(max_length=20, blank=True, null=True)
	po_box_regex = re.compile(r'\bP(ost|ostal)?([ \.]*(O|0)(ffice)?)?([ \.]*(B)(ox)?)?\b', flags=re.IGNORECASE)
	military_regex = re.compile(r'\b[AFD]PO\b', flags=re.IGNORECASE)

	class Meta:
		abstract = True

	def __str__(self):
		return self.formatted(include_name=True)

	def address_lines(self, max_lines=2, max_chars=50):
		"Split address line into multiple lines respecting max_chars per line"

		def test_lines(lines, max_lines=max_lines, max_chars=max_chars):
			return len(lines) <= max_lines and all([len(line) <= max_chars for line in lines])

		lines = None

		# Try to split by comma first
		address = self.street_address.split(',', 1)
		if len(address) > 1:
			lines = [address[0].strip(), address[1].strip()]

		# Try to split by apt/unit/#
		if not lines or not test_lines(lines):
			for item in [' apt', ' apartment', ' suite', ' unit', ' #']:
				address = re.split(item, self.street_address, maxsplit=1, flags=re.IGNORECASE)
				if len(address) > 1:
					lines = [address[0], self.street_address[len(address[0]):].strip()]

		# Finally split into lines
		if not lines or not test_lines(lines):
			lines = wrap(self.street_address, max_chars)

		while len(lines) < max_lines:
			lines = lines + ['']

		return lines[:max_lines]

	def formatted(self, include_name=False):
		name = '{}, '.format(self.name) if getattr(self, 'name') and include_name else ''

		if not getattr(self, 'street_address'):
			return ''
		address = '{}{}, {}'.format(name, self.street_address, self.city)
		if self.locality:
			address += ' ' + self.locality.abbreviation

		address += ' ' + self.postal_code + ', ' + self.country.iso_code_3
		return address

	def locality_attr(self, attr):
		if self.locality:
			return getattr(self.locality, attr)

	@property
	def street_address(self):
		"""
		If we are using address2 then this is {address}, {address2}
		Otherwise this is just {address}
		"""
		if self.address2:
			return '{}, {}'.format(self.address, self.address2)
		return self.address

	@property
	def is_military(self):
		try:
			return bool(self.military_regex.search('{} {}'.format(self.street_address, self.city)))
		except TypeError:
			pass

	@property
	def is_po_box(self):
		try:
			return self.po_box_regex.match(self.street_address)
		except TypeError:
			pass

	@property
	def phone_digits(self):
		return re.sub(r'\D', '', self.phone)


class MultiSearchChangeList(ChangeList):

	def __init__(self, *a):
		super().__init__(*a)

	def get_queryset(self, request):
		# First, we collect all the declared list filters.
		(self.filter_specs, self.has_filters, remaining_lookup_params, use_distinct) = self.get_filters(request)

		# Then, we let every list filter modify the queryset to its liking.
		qs = self.root_queryset
		for filter_spec in self.filter_specs:
			new_qs = filter_spec.queryset(request, qs)
			if new_qs is not None:
				qs = new_qs

		try:
			# Finally, we apply the remaining lookup parameters from the query
			# string (i.e. those that haven't already been processed by the
			# filters).
			qs = qs.filter(**remaining_lookup_params)
		except((SuspiciousOperation, ImproperlyConfigured)):
			# Allow certain types of errors to be re-raised as-is so that the
			# caller can treat them in a special way.
			raise
		except(Exception) as e:
			# Every other error is caught with a naked except, because we don't
			# have any other way of validating lookup parameters. They might be
			# invalid if the keyword arguments are incorrect, or if the values
			# are not in the correct type, so we might get FieldError,
			# ValueError, ValidationError, or ?.
			raise IncorrectLookupParameters(e)

		# Use select_related() if one of the list_display options is a field
		# with a relationship and the provided queryset doesn't already have
		# select_related defined.
		if not qs.query.select_related:
			if self.list_select_related:
				qs = qs.select_related()
			else:
				for field_name in self.list_display:
					try:
						field = self.lookup_opts.get_field(field_name)
					except models.FieldDoesNotExist:
						pass
					else:
						if isinstance(field.rel, models.ManyToOneRel):
							qs = qs.select_related()
							break

		# Set ordering.
		ordering = self.get_ordering(request, qs)
		qs = qs.order_by(*ordering)

		# Apply keyword searches.
		def construct_search(field_name):
			if field_name.startswith('^'):
				return "%s__istartswith" % field_name[1:]
			elif field_name.startswith('='):
				return "%s__iexact" % field_name[1:]
			elif field_name.startswith('@'):
				return "%s__search" % field_name[1:]
			else:
				return "%s__icontains" % field_name

		if self.search_fields and self.query:
			orm_lookups = [construct_search(str(search_field)) for search_field in self.search_fields]
			or_queries = []
			terms = re.split(',\W*', self.query)
			if len(terms) > 5:
				error(request, 'Searches for more than 5 terms are not allowed.')
			for bit in terms[:5]:
				or_queries += [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
			if len(or_queries) > 0:
				qs = qs.filter(reduce(operator.or_, or_queries))
			if not use_distinct:
				for search_spec in orm_lookups:
					if lookup_needs_distinct(self.lookup_opts, search_spec):
						use_distinct = True
						break

		if use_distinct:
			return qs.distinct()
		else:
			return qs


class MultiSearchModelAdmin(admin.ModelAdmin):

	def get_changelist(*a, **k):
		return MultiSearchChangeList


class ZeroExtraInline:

	def get_extra(self, request, obj=None, **kwargs):
		if obj:
			return 0
		return super().get_extra(request, obj, **kwargs)


class ProxyCastMixin(object):

	@classmethod
	def cast_proxy(cls, obj):
		obj.__class__ = cls
		return obj
