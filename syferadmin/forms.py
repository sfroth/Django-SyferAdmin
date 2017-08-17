from functools import partial

from django import forms
from django.conf import settings
from django.contrib.auth.forms import ReadOnlyPasswordHashField, ReadOnlyPasswordHashWidget as AuthReadOnlyPasswordHashWidget
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Manager
from django.core.exceptions import ValidationError
from django.forms.fields import Field
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import urlize

from .fields import UploadField, DateField, DateTimeField, PermissionField
from .middleware.threadlocal import get_request
from .models import Setting, Image, User, Meta, Region, UserNote
from .mixins import AlignmentMixin, MetaFormSet, TextAlignmentMixin
from .uploader.helpers import UploadedFile
from .utils import is_int
from .widgets import AlignmentWidget, Date, DateTime, TextAlignmentWidget, Uploader

# Add custom checkbox check
setattr(Field, 'is_checkbox', lambda self: isinstance(self.widget, forms.CheckboxInput))

FIELD_TYPES = {
	"bool": (forms.BooleanField, forms.CheckboxInput, {}),
	"choice": (forms.ChoiceField, forms.Select, {}),
	"date": (DateField, Date, {}),
	"datetime": (DateTimeField, DateTime, {}),
	"email": (forms.EmailField, forms.EmailInput, {}),
	"int": (forms.IntegerField, forms.NumberInput, {}),
	"number": (forms.IntegerField, forms.NumberInput, {}),
	"select": (forms.ChoiceField, forms.Select, {}),
	"select_multiple": (forms.MultipleChoiceField, forms.SelectMultiple, {}),
	"float": (forms.FloatField, forms.NumberInput, {}),
	"textarea": (forms.CharField, forms.Textarea, {}),
	"password": (forms.CharField, forms.PasswordInput, {'render_value': True}),
	"url": (forms.URLField, forms.URLInput, {}),
}


class Form(forms.Form):

	def __init__(self, *args, **kwargs):
		kwargs['label_suffix'] = mark_safe('<span class="suffix">:</span>')
		super(Form, self).__init__(*args, **kwargs)


class ModelForm(forms.ModelForm):

	def __init__(self, *args, **kwargs):
		kwargs['label_suffix'] = mark_safe('<span class="suffix">:</span>')
		super(ModelForm, self).__init__(*args, **kwargs)


class ActivatableForm(ModelForm):

	def __init__(self, *args, **kwargs):
		super(ActivatableForm, self).__init__(*args, **kwargs)
		self.fields['active'].initial = True


class RegionAdminForm(ModelForm):
	pass


class RegionForm(ModelForm):
	"All regional model forms should inherit this to set default regions to user's regions"

	def __init__(self, *args, **kwargs):
		super(RegionForm, self).__init__(*args, **kwargs)
		if 'regions' in self.fields:
			self.fields['regions'].initial = get_request().user.regions.all()

	def clean(self, *args, **kwargs):
		obj = self.instance
		regions = self.cleaned_data.get('regions', Region.objects.all())
		for region in regions:
			if not region.verify_unique_by_region(cleaned_data=self.cleaned_data, obj=obj):
				raise ValidationError('{} with url "{}" already exists for region {}'.format(obj.__class__.__name__, obj.slug, region))

		return self.cleaned_data


class RuleFactoryForm(ModelForm):
	"""
	Form that can support sub-fields to get serialized into a common `vars` field
	"""
	type = forms.CharField(widget=forms.HiddenInput())
	vars = forms.CharField(required=False, widget=forms.HiddenInput())

	def __init__(self, instance=None, *args, **kwargs):
		super(RuleFactoryForm, self).__init__(*args, instance=instance, **kwargs)
		if instance:
			for field in self.variable_fields():
				self.fields[field].initial = instance.vars[field]

	def clean(self):
		"Compare fields of subclass form with this one and construct a vars dict for the vars JSON field"
		cleaned_data = super(RuleFactoryForm, self).clean()
		try:
			self.cleaned_data['vars'] = {field: cleaned_data[field] for field in self.variable_fields()}
		except KeyError:
			self.cleaned_data['vars'] = {}
			raise forms.ValidationError("Please enter the missing data in this rule.")
		return self.cleaned_data

	def variable_fields(self):
		"Get fields that differ between form subclasses"
		return list(set(self.__class__.base_fields) - set(RuleFactoryForm.base_fields))


class RuleForm(ModelForm):
	fieldset_template = "admin/includes/admin_rule_fieldset.html"


class SchedulableForm(ModelForm):
	start_date = DateTimeField(required=False, label='Start date (optional)')
	end_date = DateTimeField(required=False, label='End date (optional)')


class SettingsForm(Form):
	"Form for settings - creates a field for each config variable"

	def __init__(self, settings, *args, **kwargs):
		super(SettingsForm, self).__init__(*args, **kwargs)
		self.add_fields(settings)

	def add_fields(self, settings):
		"Recursively add settings field to the form"
		for setting in sorted(list(settings), key=lambda x: (x.key)):
			if hasattr(setting, 'children'):
				self.add_fields(setting)
			else:
				field_class, field_widget, field_widget_args = FIELD_TYPES.get(setting.type, (forms.CharField, forms.TextInput, {}))
				attrs = {}
				# Prevent password autocomplete in chrome
				if setting.type == 'password':
					attrs['autocomplete'] = 'new-password'
				if setting.placeholder:
					attrs['placeholder'] = setting.placeholder
				field_widget_args['attrs'] = attrs
				kwargs = {
					"label": mark_safe(' '.join((setting.get_name(), self.format_help(setting.description)))),
					"initial": field_class().to_python(setting.get_value()),
					"required": False,
					"widget": field_widget(**field_widget_args)
				}
				if setting.type in ['choice', 'select', 'select_multiple']:
					kwargs['choices'] = setting.options
				self.fields[setting.key] = field_class(**kwargs)
				self.fields[setting.key].default = setting.default
				setting.form_field = self[setting.key]

	def save(self):
		"Save each of the settings to the DB."
		region = Region.objects.filter(slug=self.data.get('current_region')).first()

		for (name, value) in self.cleaned_data.items():
			setting, created = Setting.objects.get_or_create(key=name, region=region)
			setting.value = value

			# Get default setting if saving for region
			default_setting = None
			if region:
				default_setting = Setting.objects.filter(key=name, region=None).first()

				if default_setting and str(setting.value) == default_setting.value:
					setting.delete()
				elif self.fields[name].default and setting.value == self.fields[name].default:
					setting.delete()
				else:
					setting.save()

			else:
				if self.fields[name].default and setting.value == self.fields[name].default:
					setting.delete()
				elif not self.fields[name].default and not setting.value:
					setting.delete()
				else:
					setting.save()

	def format_help(self, description):
		"Format the setting's description into HTML."
		if not description:
			return ''
		for bold in ("``", "*"):
			parts = []
			for i, s in enumerate(description.split(bold)):
				parts.append(s if i % 2 == 0 else "<b>%s</b>" % s)
			html_description = "".join(parts)
		return '<span class="help" tabindex="-1" data-content="' + description + '" title="' + description + '"><span>' + urlize(html_description).replace("\n", "<br>") + '</span></span>'


class UploadsForm(object):
	"""
	Any form that uses uploads can extend this to automatically implement the necessary
	`clean_xxx` method(s) and automatic upload file handling on save
	"""
	cleaned_uploads = {}

	def __init__(self, *args, **kwargs):
		super(UploadsForm, self).__init__(*args, **kwargs)

		# Find upload fields
		self.upload_fields = [name for name, field in self.fields.items() if type(field) is UploadField]
		self.cleaned_uploads = {}
		self.groups = {}
		self.descriptions = {}

		# Create dynamic clean method
		def clean_uploads(field, self):
			field_name = "{0}-{1}".format(self.prefix, field) if self.prefix else field
			self.cleaned_uploads[field] = self.data.getlist(field_name)
			self.groups[field] = self.data.getlist('{}_group'.format(field_name))
			self.descriptions[field] = self.data.getlist('{}_description'.format(field_name))
			return self.cleaned_uploads[field]

		# Set clean method dynamically
		for field in self.upload_fields:
			setattr(self, 'clean_{0}'.format(field), partial(clean_uploads, field, self))

			if self._meta.fields:
				if field in self._meta.fields:
					self._meta.fields.remove(field)

			# Set existing uploads in the widget
			try:
				existing_uploads = getattr(self.instance, field)
				if existing_uploads:
					if isinstance(existing_uploads, Manager):
						existing_uploads = existing_uploads.all()
					elif type(existing_uploads) is not list:
						existing_uploads = [existing_uploads]
					self.fields[field].widget.uploads = existing_uploads
			except AttributeError:
				pass

	def save(self, commit=True):
		"Save override to save files after save"

		instance = super(UploadsForm, self).save(commit)
		original_m2m = getattr(self, 'save_m2m', None)

		def save_m2m():
			if original_m2m:
				original_m2m()
			self.save_files(instance)

		if commit:
			self.save_files(instance)
			if original_m2m:
				original_m2m()
		else:
			self.save_m2m = save_m2m

		return instance

	def save_files(self, instance):
		"Save associated images/files"

		# Note differences in submitted vs existing
		for field in self.upload_fields:
			submitted_files = self.cleaned_uploads[field]
			existing_files = getattr(instance, field, [])
			if isinstance(existing_files, Manager):
				existing_files = existing_files.all()
				deleted_files = [i for i in existing_files if i and i.image not in submitted_files]
			else:
				if not type(existing_files) is list:
					existing_files = [existing_files]
				deleted_files = [i for i in existing_files if i and i not in submitted_files]
			new_files = [file_id for file_id in submitted_files if UploadedFile.create(file_id).valid()]

			# Delete images
			for file_obj in deleted_files:
				file_obj.delete()

			# New images
			if isinstance(getattr(instance, field), Manager):
				for i, file_id in enumerate(new_files):
					image = Image()
					image.content_object = instance
					image.image = UploadedFile.create(file_id).to_file()
					# If names are not unique, files will be overwritten
					try:
						last_image = sorted([int(item.name) for item in existing_files if is_int(item.name)])[-1]
					except:
						last_image = 0
					image.name = str(int(last_image) + (i + 1))
					image.sort = submitted_files.index(file_id)
					try:
						image.group = self.groups[field][image.sort] if self.groups[field][image.sort] else None
					except (KeyError, IndexError):
						image.group = None
					try:
						image.description = self.descriptions[field][image.sort] if self.descriptions[field][image.sort] else ''
					except (KeyError, IndexError):
						image.description = ''
					image.save()
			else:
				for file_id in new_files:
					file_obj = UploadedFile.create(file_id).to_file()
					getattr(instance, field).save(file_obj.name, file_obj)

			# Old images
			if isinstance(getattr(instance, field), Manager):
				for i, image in enumerate(existing_files):
					try:
						image.sort = submitted_files.index(image.image)
						try:
							image.group = self.groups[field][image.sort] if self.groups[field][image.sort] else None
						except (KeyError, IndexError):
							image.group = None
						try:
							image.description = self.descriptions[field][image.sort] if self.descriptions[field][image.sort] else ''
						except (KeyError, IndexError):
							image.description = ''
						image.save()
					except Exception:
						pass


class UserCreationForm(ModelForm):
	"""
	Copied from django/forms/forms.py (Required for Custom User Model)
	"""
	error_messages = {
		'duplicate_username': _("A user with that username already exists."),
		'password_mismatch': _("The two password fields didn't match."),
	}
	username = forms.RegexField(label=_("Username (optional)"), required=False, max_length=30,
		regex=settings.SYFERADMIN_USER_USERNAME_REGEX,
		help_text=_("30 characters or fewer. Letters, digits and "
					"@/./+/-/_ only."),
		error_messages={
			'invalid': _("This value may contain only letters, numbers and "
						"@/./+/-/_ characters.")})
	email = forms.EmailField(label='Email address')
	password1 = forms.CharField(label=_("Password"),
		widget=forms.PasswordInput)
	password2 = forms.CharField(label=_("Password confirmation"),
		widget=forms.PasswordInput,
		help_text=_("Enter the same password as above, for verification."))

	class Meta:
		model = User
		fields = ("email", "username")

	def clean_username(self):
		# Since User.username is unique, this check is redundant,
		# but it sets a nicer error message than the ORM. See #13147.
		username = self.cleaned_data["username"]
		if not username:
			return ''
		try:
			User._default_manager.get(username=username)
		except User.DoesNotExist:
			return username
		raise forms.ValidationError(
			self.error_messages['duplicate_username'],
			code='duplicate_username',
		)

	def clean_password2(self):
		password1 = self.cleaned_data.get("password1")
		password2 = self.cleaned_data.get("password2")
		if password1 and password2 and password1 != password2:
			raise forms.ValidationError(
				self.error_messages['password_mismatch'],
				code='password_mismatch',
			)
		return password2

	def save(self, commit=True):
		user = super(UserCreationForm, self).save(commit=False)
		user.set_password(self.cleaned_data["password1"])
		if commit:
			user.save()
		return user


class RelatedForm(ModelForm):

	class Meta:
		widgets = {
			'sort': forms.HiddenInput(),
			'related_content_type': forms.HiddenInput(),
			'related_object_id': forms.HiddenInput(),
			'group': forms.HiddenInput(),
		}


class PageMetaFormSet(MetaFormSet):
	meta_keys = (('page_title', 'Title'), ('page_description', 'Description'))


class MetaForm(ModelForm):
	key = forms.CharField(widget=forms.HiddenInput())
	value = forms.CharField(required=False)

	class Meta:
		model = Meta
		fields = ('key', 'value')

	def save(self, commit=True):
		"""Overide form save to reconstruct empty value instances that get lost"""
		if self.instance.pk is None:
			fail_message = 'created'
		else:
			fail_message = 'changed'
		return forms.save_instance(self, self.instance, self._meta.fields, fail_message, commit, self._meta.exclude, construct=True)


class ExcludedPermissionsForm(object):
	EXCLUDED_APPS = [
		'contenttypes',
		'core',
		'djcelery',
		'sessions',
		'sites',
	]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields:
			if isinstance(self.fields[field], PermissionField):
				self.fields[field].queryset = self.fields[field].queryset.exclude(content_type__app_label__in=self.EXCLUDED_APPS)


class ReadOnlyPasswordHashWidget(AuthReadOnlyPasswordHashWidget):

	def render(self, *args, **kwargs):
		rendered = super(ReadOnlyPasswordHashWidget, self).render(*args, **kwargs)
		return mark_safe(rendered + '<a href="../password/" class="btn">Update Password</a>')


class UserChangeForm(ExcludedPermissionsForm, ModelForm):
	"""
	Copied from django/forms/forms.py (Required for Custom User Model)
	"""
	username = forms.RegexField(
		label=_("Username (optional)"), max_length=30, required=False, regex=settings.SYFERADMIN_USER_USERNAME_REGEX,
		help_text=_("30 characters or fewer. Letters, digits and "
					"@/./+/-/_ only."),
		error_messages={
			'invalid': _("This value may contain only letters, numbers and "
						"@/./+/-/_ characters.")})
	password = ReadOnlyPasswordHashField(label=_("Password"), widget=ReadOnlyPasswordHashWidget)
	# user_permissions = PermissionField(queryset=Permission.objects.all().select_related('content_type'), required=False)

	class Meta:
		model = User
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super(UserChangeForm, self).__init__(*args, **kwargs)
		f = self.fields.get('user_permissions', None)
		if f is not None:
			f.queryset = f.queryset.select_related('content_type')

	def clean_password(self):
		# Regardless of what the user provides, return the initial value.
		# This is done here, rather than on the field, because the
		# field does not have access to the initial value
		return self.initial["password"]


class UserGroupForm(ExcludedPermissionsForm, ModelForm):
	# permissions = PermissionField(queryset=Permission.objects.all().select_related('content_type'), required=False)

	class Meta:
		model = Group
		fields = '__all__'


class VideoForm(ModelForm):
	key = forms.CharField(widget=forms.HiddenInput())
	type = forms.CharField(widget=forms.HiddenInput())
	thumb = forms.CharField(required=False, widget=forms.HiddenInput())
	height = forms.CharField(required=False, widget=forms.HiddenInput())
	width = forms.CharField(required=False, widget=forms.HiddenInput())

	class Meta:
		widgets = {
			'sort': forms.HiddenInput(),
		}


class ReportDatesForm(Form):
	start_date = DateField()
	end_date = DateField()


class DateRangeForm(Form):
	"Date range form for admin filtering"

	def __init__(self, request, *args, **kwargs):
		field_name = kwargs.pop('field_name')
		fields = [('{}__gte'.format(field_name), 'Start date'), ('{}__lte'.format(field_name), 'End date')]

		# Inject values for the other filter
		for other_field, value in request.GET.items():
			if other_field not in [f for f, l in fields]:
				kwargs['data'][other_field] = value

		super().__init__(*args, **kwargs)

		# Range fields
		for field, label in fields:
			self.fields[field] = DateField(label=label, localize=True, required=False)

		# Hidden inputs for other active filters
		for other_field, value in request.GET.items():
			if other_field not in [f for f, l in fields]:
				self.fields[other_field] = forms.CharField(initial=value, widget=forms.HiddenInput(), required=False)
				self.fields[other_field].initial = value


class UserNoteForm(forms.ModelForm):

	class Meta:
		model = UserNote
		fields = ['key', 'content']
		widgets = {
			'key': forms.Select(),
			'content': forms.Textarea(attrs={'rows': 1})
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if UserNote.types():
			self.fields['key'].widget.choices = UserNote.types()
		else:
			del self.fields['key']
