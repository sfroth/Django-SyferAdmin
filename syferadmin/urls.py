from django.conf.urls import url
from django.contrib.auth.views import password_reset, password_reset_done, password_reset_confirm, password_reset_complete
from .reports import Report
from syferadmin.views import videos, related, foreignkey_search, oauth, reports, emails
from syferadmin.uploader import views as uploader_views


urlpatterns = [

	# Uploader urls
	url(r'^uploader/add/$', uploader_views.add, name='upload_file'),
	url(r'^uploader/check/(?P<uuid>[\.\w-]+)/?', uploader_views.check, name='check_uploaded_file'),
	url(r'^uploader/delete/(?P<uuid>[-\w]+)/?', uploader_views.delete, name='delete_uploaded_file'),

	# Videos
	url(r'^video/add/$', videos.add, name='add_video'),

	# Related model lookup
	url(r'^related_lookup/$', related.lookup, name='related_lookup'),

	# Ajax Search lookup
	url(r'^foreignkey_search/(?P<content_type_id>[\d]+)/$', foreignkey_search.ajax_search, name='foreignkey_search'),

	# Release Notes
	# Temporarily disable for further improvement
	# url(r'^releasenotes/', 'views.releasenotes.recent', name='releasenotes'),

	# Reports
	url(r'^reports/authorize/', oauth.authorize, name='reports_authorize'),
	url(r'^reports/authorized/', oauth.authorized, name='reports_authorized'),
	url(r'^reports/detail/(.+)/', reports.report_detail, name='report_detail'),
	url(r'^reports/poll/', reports.poll_report_state, name='poll_report_state'),
	url(r'^reports/export/(?P<token>[^/]+)(?:/(?P<export_as>(csv|xl)))?/', reports.export, name='report_export'),
	url(r'^reports/(.+)/', reports.detail, name='report'),

	# Password Reset
	url(r'^password-reset/$', password_reset,
		{'post_reset_redirect': 'admin_password_reset_done', 'email_template_name': 'registration/password_reset_email.html'}, name='admin_password_reset'),
	url(r'^password-reset/sent/$', password_reset_done, name='admin_password_reset_done'),
	url(r'^password-reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', password_reset_confirm,
		{'post_reset_redirect': 'admin_password_reset_complete'}, name='admin_password_reset_confirm'),
	url(r'^password-reset/complete/$', password_reset_complete,
		{'template_name': 'registration/password_reset_complete.html'}, name='admin_password_reset_complete'),

	# Email viewing
	url(r'^emails(?:/(?P<email_type>[a-zA-Z-]+))?(?:/(?P<param>[0-9]+))?/$', emails.email_test, name='emails'),

	# Dynamic report URLs
	# *[url(r'^reports/detail/{}/'.format(report.token), 'views.reports.report_detail', name='{}_report'.format(report.token)) for report in Report.objects.all()]

]
