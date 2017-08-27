import itertools
import copy
from functools import partial

from django import forms as django_forms
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets, unquote
from django.contrib.admin.options import modelform_factory
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.contrib.contenttypes.admin import GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import success, error
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import NoReverseMatch, reverse
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string

from . import filters, forms, BaseSection, AdminSection
from .mixins import ActionsAdmin, ActivatableAdmin, MetaInline, RegionalAdmin, SchedulableAdmin, MultiSearchModelAdmin, MultiSearchChangeList
from .models import Related, Setting, User, Video, Meta, Region
from .reports import Report
from .settings import Settings
from .utils import human_join


class SyferAdminAuthenticationForm(AuthenticationForm):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['username'].widget = django_forms.TextInput(attrs={'placeholder': 'Username'})
		self.fields['password'].widget = django_forms.PasswordInput(attrs={'placeholder': 'Password'})


class SyferAdmin(admin.AdminSite):
	"""
	SyferAdmin extends the default AdminSite adding some custom functionality, such
	as tracking sections to build a custom navigation and a dashboard
	"""
	sections = {}
	login_form = SyferAdminAuthenticationForm

	def get_urls(self):
		"Override of AdminSite.get_urls() to set a custom dashboard"
		from django.conf.urls import url

		urls = super().get_urls()
		urls = [
			url(r'^$', self.admin_view(self.index), name='dashboard'),
		] + urls
		return urls

	def index(self, request):
		"Dashboard view"
		from django.conf import settings
		from .forms import ReportDatesForm
		from .models import Setting
		from .reports import Report

		context = {}

		# if not settings.Admin.Reporting.google_analytics_view_id:
		# 	error(request, 'We\'ll need your Google Analytics View ID to receive reports on your dashboard. <a href="/admin/syferadmin/setting/Admin/">Go to Admin settings</a>.')
		# 	context['error'] = True
		# else:
		# 	try:
		# 		Setting.objects.get(key='Site.google_analytics_oauth_code')
		# 	except Setting.DoesNotExist:
		# 		error(request, 'To display reports on your dashboard, we\'ll need access to your Google Analytics account. <a class="authorize" href="reports/authorize/">Authorize now</a>.')
		# 		context['error'] = True
		context['show_filters'] = False

		context['containers'] = [{'name': container[0] or '', 'reports': Report.objects.filter(container[1])} for container in settings.SYFERADMIN_DASHBOARD_MODULES]
		context['form'] = ReportDatesForm()
		dashboard_reports = list(itertools.chain.from_iterable([Report.objects.filter(container[1]) for container in settings.SYFERADMIN_DASHBOARD_MODULES]))
		filters = []
		# Clone report so that filters don't get applied to the in-memory version
		dashboard_reports = [copy.copy(report) for report in dashboard_reports]
		filter_option_list = {}
		for report in dashboard_reports:
			# Set prefiltering for region?
			report.filter_current_region = settings.SYFERADMIN_DASHBOARD_FILTER_TO_CURRENT_REGION

			if hasattr(report, 'filters') and report.filters:
				report_request = {
					'report': request.GET,
					'region': request.region,
					'user': request.user,
				}
				filters.extend([fltr for fltr in report.filters if fltr not in filters])
				report.set_request(report_request)
				filter_option_list.update(report.filter_option_list())
				context['show_filters'] = True
		selected_filters = {}
		if 'site_region' not in request.GET and settings.SYFERADMIN_DASHBOARD_FILTER_TO_CURRENT_REGION:
			selected_filters['site_region'] = request.region.slug
		for fltr in filters:
			if fltr[1] in request.GET and request.GET[fltr[1]]:
				selected_filters[fltr[1]] = request.GET[fltr[1]]
		context['filters'] = filters
		context['filter_option_list'] = filter_option_list
		context['selected_filters'] = selected_filters
		return TemplateResponse(request, 'admin/dashboard.html', context)

	def logout(self, request, extra_context=None):
		"Logout override to redirect after logout"
		from django.contrib.auth.views import logout
		from django.core.urlresolvers import reverse
		defaults = {
			'current_app': self.name,
			'extra_context': extra_context or {},
			'next_page': request.GET.get('next', reverse('admin:dashboard')),
		}
		if self.logout_template is not None:
			defaults['template_name'] = self.logout_template
		return logout(request, **defaults)

	def register(self, model_or_iterable, admin_class=None, **options):
		"Register new admin section and also add to a section group"

		# If model_or_iterable is a string lookup the model
		if type(model_or_iterable) is str:
			model_or_iterable = django_apps.get_model(*model_or_iterable.split('.', 1))

		# If admin_class is a string, lookup the class
		if type(admin_class) is str:
			admin_class = import_string(admin_class)

		# Pop off syferadmin-specific options before calling super(), so only applicable
		# options are passed along
		position = options.pop('position', 5)  # Sub section position in navigation (0-10)
		active_url_token = options.pop('active_url_token', None)  # Alternative URL token to match for active status
		force = options.pop('force', False)
		ignore_section = options.pop('ignore_section', False)

		# Unregister on force
		if force:
			self.unregister(model_or_iterable)

		super().register(model_or_iterable, admin_class, **options)

		# Ignore falsey entries
		# @TODO Instead the unregister method should support removing sections
		if ignore_section or getattr(admin_class, 'section', None) is False:
			return self

		# Create a section for admin navigation
		sub_section = {
			'text': getattr(admin_class, 'name', model_or_iterable._meta.verbose_name_plural.title()),
			'app': "_".join([model_or_iterable._meta.app_label, model_or_iterable._meta.model_name]),
			'group': getattr(admin_class, 'group', False),
			'model': model_or_iterable,
			'admin': admin_class(model_or_iterable, self),
			'position': position,
			'active_url_token': active_url_token,
		}
		# Grab custom section, or AdminSection
		section = getattr(admin_class, 'section', AdminSection)

		# Add subsection to top-level section
		self.sections.setdefault(section.name, section()).children.append(sub_section)


site = SyferAdmin()


class ContentSection(BaseSection):
	name = 'Content'
	title = 'Site Content'
	token = 'content'
	position = 3


class GroupAdmin(ActionsAdmin, auth_admin.GroupAdmin):
	group = 'Users'
	actions = None
	filter_horizontal = ()  # This is needed to override the ridiculous widgets the admin selects for ManyToManyFields
	form = forms.UserGroupForm


class SettingsAdmin(admin.ModelAdmin):
	"Admin class for editing Settings"

	class Media:
		js = ('syferadmin/js/settings.js',)

	def change_view(self, request, section, **kwargs):
		"Settings edit"

		if not self.has_change_permission(request, None):
			raise PermissionDenied

		region = request.GET.get('region', None)

		try:
			settings = getattr(Settings.load(region=Region.objects.filter(slug=region).first()), section.title())
		except KeyError:
			raise Http404
		form = forms.SettingsForm(settings, request.POST or None, label_suffix='')
		if form.is_valid():
			form.save()

			history = self.get_history_id()
			if history:
				region_label = region.upper() if region else 'Default'
				admin.models.LogEntry.objects.log_action(
					action_flag=admin.models.CHANGE,
					change_message='Changed {} Fields {}'.format(region_label, human_join(form.changed_data)),
					content_type_id=ContentType.objects.get_for_model(self.model).pk,
					object_id=history,
					object_repr='{} Settings'.format(region_label),
					user_id=request.user.pk,
				)

			Settings.reload()
			success(request, "Settings saved!")
			return redirect("admin:syferadmin_setting_changelist")
		context = {'settings_list': settings, 'section': section.title(), 'regions': Region.objects.all(), 'current_region': region, 'form': form}
		return render(request, 'syferadmin/settings/admin_edit.html', context)

	def changelist_view(self, request, **kwargs):
		"Setting list view override"

		if not self.has_change_permission(request, None):
			raise PermissionDenied

		history = self.get_history_id()

		return render(request, 'syferadmin/settings/admin_index.html', {'settings_list': Settings.load(), 'media': self.media, 'history': history})

	def has_add_permission(self, request):
		return False

	def get_history_id(self):
		try:
			return Setting.objects.get(key='Company.name', region=None).pk
		except (Setting.DoesNotExist, Setting.MultipleObjectsReturned):
			pass
		return False


class RegionAdmin(ActionsAdmin, admin.ModelAdmin):
	actions = None
	form = forms.RegionAdminForm
	list_display = ('name', 'slug')
	model = Region
	section = AdminSection

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


class RelatedInlineFormset(BaseGenericInlineFormSet):

	def __init__(self, data=None, files=None, instance=None, save_as_new=None,
					prefix=None, queryset=None, **kwargs):
		super().__init__(data=data, files=files, instance=instance, save_as_new=save_as_new,
					prefix=prefix, queryset=queryset, **kwargs)
		if instance is not None and instance.pk is not None:
			instance.delete_related_orphans()
			self.queryset = self.queryset.filter(group__in=[k[0] for k in instance.get_related_models()])


class RelatedInline(GenericStackedInline):
	model = Related
	form = forms.RelatedForm
	formset = RelatedInlineFormset
	template = 'related/admin_related_inline.html'
	extra = 0

	class Media:
		css = {'all': ('syferadmin/css/related-inline.css',)}
		js = ('syferadmin/js/related-inline.js', 'syferadmin/js/model-browser-widget.js')


class UserActionFilter(admin.SimpleListFilter):
	title = 'Action Type'

	# Parameter for the filter that will be used in the URL query.
	parameter_name = 'action_type'

	def lookups(self, request, model_admin):
		return (
			('1', 'Created'),
			('2', 'Modified'),
			('3', 'Deleted'),
		)

	def queryset(self, request, queryset):
		if self.value():
			return queryset.filter(action_flag=self.value())
		return queryset


class UserActivityAdmin(admin.ModelAdmin):
	list_display = ('date_display', 'action_display', 'content_display', 'record_display')
	list_display_links = (None,)
	list_filter = ['action_time', UserActionFilter]
	actions = None
	search_fields = ['content_type__model', 'content_type__app_label', 'content_type__model', 'object_repr', 'change_message']

	def action_display(self, obj):
		if obj.is_addition():
			return 'Created'
		if obj.is_change():
			return 'Modified'
		return 'Deleted'
	action_display.admin_order_field = 'action_flag'
	action_display.short_description = 'Action'

	def content_display(self, obj):
		title = str(obj.content_type).title()
		# Try in case of old content types, eg: overridden mantles
		try:
			url = reverse('admin:{}_{}_changelist'.format(obj.content_type.app_label, obj.content_type.model))
			return '<a href="{}">{}</a>'.format(url, title)
		except NoReverseMatch:
			return title
	content_display.admin_order_field = 'content_type_id'
	content_display.allow_tags = True
	content_display.short_description = 'Content'

	def date_display(self, obj):
		return obj.action_time
	date_display.admin_order_field = 'action_time'
	date_display.short_description = 'Date'

	def record_display(self, obj):
		title = obj.object_repr.title()
		try:
			url = reverse('admin:{}_{}_change'.format(obj.content_type.app_label, obj.content_type.model), args=[obj.object_id])
			return '<a href="{}" title="{}">{}</a>'.format(url, obj.change_message, title)
		except NoReverseMatch:
			return title
	record_display.admin_order_field = 'object_id'
	record_display.allow_tags = True
	record_display.short_description = 'Record'

	def get_queryset(self, request):
		actions = super().get_queryset(request)
		return actions.filter(user=request.user_actions)

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request):
		return False


class UserAdmin(RegionalAdmin, ActionsAdmin, auth_admin.UserAdmin):
	actions = None
	add_fieldsets = (
		(None, {'fields': ('name', 'email', 'password1', 'password2', 'is_staff', 'is_superuser')}),
	)
	add_form = forms.UserCreationForm
	add_form_template = None
	change_form_template = 'admin/admin_user_edit.html'
	fieldsets = (
		(_('User Info'), {'fields': ('email', 'password')}),
		(_('Personal info'), {'fields': ('name',)}),
		(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups',)}),  # 'user_permissions',)}),
	)
	filter_horizontal = ()  # This is needed to override the ridiculous widgets the admin selects for ManyToManyFields
	form = forms.UserChangeForm
	list_display = ('email', 'name', 'is_staff', 'last_login',)
	ordering = ('-is_staff', 'email')
	search_fields = ('name', 'email')

	class Media:
		js = ('syferadmin/js/user.js',)

	def activity(self, request, user_id):
		"View all codes for a given promotion"
		from django.contrib.admin.models import LogEntry
		request.user_actions = get_object_or_404(User, pk=user_id)
		return UserActivityAdmin(LogEntry, site).changelist_view(request, {'user_actions': request.user_actions})

	def change_view(self, request, object_id, form_url='', extra_context={}):
		"Change view override"
		user = self.get_object(request, unquote(object_id))
		extra_context = {
			'logins': user.userlogin_set.all()[:10],
		} if user else {}
		return super().change_view(request, object_id, extra_context=extra_context)

	def downgrade(self, request, object_id):
		"Upgrade customer to staff user"
		customer = self.get_object(request, unquote(object_id))
		customer.is_staff = False
		customer.is_superuser = False
		customer.save()
		success(request, "{} successfully downgraded to customer.".format(customer.email))
		return redirect(reverse('admin:syferadmin_user_changelist'))

	def get_changelist(*a, **k):
		return MultiSearchChangeList

	def get_queryset(self, request):
		queryset = super(UserAdmin, self).get_queryset(request)
		return queryset.filter(Q(is_staff=True) | Q(is_superuser=True))

	def get_urls(self):
		info = self.model._meta.app_label, self.model._meta.model_name
		urls = [
			url(r'^(.+)/downgrade/$', self.admin_site.admin_view(self.downgrade), name='%s_%s_downgrade' % info),
			url(r'^(.+)/activity/$', self.admin_site.admin_view(self.activity), name='%s_%s_activity' % info),
		]
		return urls + super().get_urls()

	def has_delete_permission(self, request, obj=None):
		return False


class VideoInline(GenericStackedInline):
	model = Video
	form = forms.VideoForm
	template = 'videos/admin_videos_inline.html'
	extra = 0

	class Media:
		css = {'all': ('syferadmin/css/video-inline.css',)}
		js = ('syferadmin/js/video-inline.js',)


class PageMetaInline(MetaInline):
	model = Meta
	formset = forms.PageMetaFormSet
	template = 'pagemeta/admin_pagemeta_inline.html'
	verbose_name = 'page meta'
	verbose_name_plural = 'page meta'


class ReportsSection(BaseSection):
	name = 'Reports'
	title = 'Reports'
	token = 'reports'
	group = 'Reports'
	position = 99


for report in Report.objects.withdetail():
	sub_section = {
		'text': report.title,
		'app': 'syferadmin_report',
		'url': '{}_report'.format(report.token),
		'group': 'Reports',
		'model': None,
		'admin': None,
		'position': 1,
		'active_url_token': report.token,
		'perm': 'syferadmin.can_view_reports'
	}
	site.sections.setdefault(ReportsSection.name, ReportsSection()).children.append(sub_section)

#
# Temporarily disable the Release Notes section for further improvement
#
# sub_section = {
# 	'text': 'Release Notes',
# 	'app': 'syferadmin_releasenotes',
# 	'url': 'releasenotes',
# 	'group': False,
# 	'model': None,
# 	'admin': None,
# 	'position': 10,
# 	'active_url_token': 'releasenotes',
# }
# site.sections.setdefault(AdminSection.name, AdminSection()).children.append(sub_section)


site.register(User, UserAdmin)
site.register(Group, GroupAdmin)
site.register(Region, RegionAdmin, ignore_section=True)
site.register(Setting, SettingsAdmin)
