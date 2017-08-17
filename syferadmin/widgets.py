from copy import deepcopy
from itertools import groupby
from operator import attrgetter

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.utils.html import format_html, mark_safe
# from django.forms.widgets import ChoiceInput

from . import json


# Monkeypatch ChoiceInput render
# def render_label_after_input(self, name=None, value=None, attrs=None, choices=()):
# 	name = name or self.name
# 	value = value or self.value
# 	attrs = attrs or self.attrs
# 	if 'id' in self.attrs:
# 		label_for = format_html(' for="{}"', self.attrs['id'])
# 	else:
# 		label_for = ''
# 	return format_html('{1}<label{0}>{2}</label>', label_for, self.tag(), self.choice_label)
# ChoiceInput.render = render_label_after_input


class AdminReadonlyImageInput(forms.Widget):
	class Media:
		css = {'all': ('syferadmin/css/upload-widget.css',)}

	def __init__(self, obj, attrs=None):
		self.object = obj
		super().__init__(attrs)

	def render(self, name, value, attrs=None):
		if value and hasattr(value, "url"):
			return mark_safe("""<div class="uploader"><ul><li>
<img src="{0}">
<a href="{1}" class="zoom">View Image</a>
</li></ul></div>""".format(self.object.resized(source=name, id='syferadmin:imageblock.thumb').url, value.url))
		else:
			return ''


class AlignmentWidget(forms.Select):
	"Make a grid of the selections"
	class Media:
		css = {
			'all': ('syferadmin/css/alignmentwidget.css',),
		}
		js = ('syferadmin/js/alignmentwidget.js',)

	def render(self, name, value, attrs=None):
		attrs = attrs or {}
		attrs['data-alignment-widget'] = '1'
		return super().render(name, value, attrs)


class TextAlignmentWidget(forms.Select):
	"Make a grid of the selections"
	class Media:
		css = {
			'all': ('syferadmin/css/textalignmentwidget.css',),
		}
		js = ('syferadmin/js/textalignmentwidget.js',)

	def render(self, name, value, attrs=None):
		attrs = attrs or {}
		attrs['data-text-alignment-widget'] = '1'
		return super().render(name, value, attrs)


class Date(forms.TextInput):
	"""
	HTML5 Date Input
	Falls back to regular text input with calendar picker
	"""
	input_type = 'date'

	class Media:
		css = {'all': ('syferadmin/libs/jquery-ui/jquery-ui.css', 'syferadmin/libs/timepicker/timepicker.css')}
		js = ('syferadmin/libs/timepicker/timepicker.js', 'syferadmin/js/datetime-widget.js')


class DateTime(Date):
	"""
	HTML5 DateTime Input
	Falls back to regular text input with calendar picker
	"""
	input_type = 'datetime-local'

	def __init__(self, attrs=None):
		attrs = {'step': 1}
		super(DateTime, self).__init__(attrs)


class Editor(forms.Textarea):

	class Media:
		css = {'all': ('syferadmin/libs/editor/editor.css',)}
		js = ('syferadmin/libs/editor/marked.js', 'syferadmin/libs/editor/editor.js', 'syferadmin/js/editor-widget.js')

	def render(self, *args, **kwargs):
		return format_html(u"""
			<div class="editor">{0}</div>""", super(Editor, self).render(*args, **kwargs))


class FileUpload(forms.ClearableFileInput):
	template_with_initial = (
		'<div class="file-upload__container">'
		'<a class="file-upload__name fancybox" title="%(value)s" href="%(initial_url)s" target="_blank">%(initial)s</a> %(clear_template)s'
		'<div class="file-upload">'
		'<label class="file-upload__label">Upload File:</label>'
		'%(input)s'
		'</div>'
		'<button type="button" class="file-upload__btn file-upload__btn--edit btn btn--edit">Edit</button>'
		'</div>'
	)

	template_with_clear = '%(clear)s <label for="%(clear_checkbox_id)s">%(clear_checkbox_label)s</label>'

	class Media:
		js = ('syferadmin/libs/fileupload/upload.js',)

	def render(self, name, value, attrs=None):
		self.template_with_initial = self.template_with_initial.replace('%(value)s', force_text(value))
		return super().render(name, value, attrs)


class ForeignKey(forms.Select):

	class Media:
		css = {'all': ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/css/select2.css',)}
		js = ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/js/select2.min.js', 'syferadmin/libs/foreignkey/search.js')

	def __init__(self, model, *args, **kwargs):
		self.model = model
		self.content_type = ContentType.objects.get_for_model(self.model)
		super().__init__(*args, **kwargs)

	def render(self, name, value, attrs=None):
		if not attrs:
			attrs = {}
		attrs['data-foreignkey_url'] = reverse('foreignkey_search', args=[self.content_type.pk])
		self.choices = [(v.pk, v) for v in self.model.objects.filter(pk=value)]
		attrs.setdefault('class', '')
		attrs['class'] += ' initialized'
		return super().render(name, value, attrs)


# class PermissionRenderer(forms.widgets.CheckboxFieldRenderer):
# 	legend = """
# 			<div class="permissions-legend">
# 				<h4>Icon Legend</h4>
# 				<dl>
# 					<dt><span class="empty-icon">Empty Icon</span></dt>
# 					<dd>No permissions</dd>
# 				</dl>
# 				<dl>
# 					<dt><span class="partial-icon">Partial Icon</span></dt>
# 					<dd>Some permissions</dd>
# 				</dl>
# 				<dl><dt><span class="filled-icon">Filled Icon</span></dt>
# 					<dd>All permissions</dd>
# 				</dl>
# 			</div>
# 			"""

# 	def render(self):
# 		"""Group the permissions by app_label and content_type and render
# 		into 3-tiered nested lists.
# 		"""
# 		permissions = [p[2] for p in self.choices]
# 		id_ = self.attrs.get('id', None)
# 		start_tag = format_html('<ul id="{0}" class="permission-apps">', id_) if id_ else '<ul>'
# 		output = [self.legend, start_tag]
# 		for app_label, app_group in groupby(permissions, attrgetter('content_type.app_label')):
# 			output.append(format_html('<li><h5 title="Enable all">{}</h5><button type="button" class="group-toggle" title="Show group">Show group</button><ul class="permission-types">'.format(app_label.title())))
# 			for content_label, content_group in groupby(app_group, attrgetter('content_type')):
# 				output.append(format_html('<li><h6>{}</h6><ul class="permission-items">'.format(str(content_label).title())))
# 				for perm in content_group:
# 					widget = self.choice_input_class(self.name, self.value, self.attrs.copy(), (perm.pk, perm.name), perm.pk)
# 					output.append(format_html('<li>{}</li>', force_text(widget)))
# 				output.append("</ul></li>")
# 			output.append("</ul></li>")
# 		output.append("</ul>")
# 		return mark_safe('\n'.join(output))


# class PermissionSelector(forms.CheckboxSelectMultiple):
# 	renderer = PermissionRenderer

# 	class Media:
# 		css = {'all': ('syferadmin/css/permissions-widget.css',)}
# 		js = ('syferadmin/js/permissions-widget.js',)


# class RegionChoiceInput(forms.widgets.CheckboxChoiceInput):

# 	def __init__(self, name, value, attrs, choice, index):
# 		"Add extra region code to each region choice input"
# 		super(RegionChoiceInput, self).__init__(name, value, attrs, choice, index)
# 		self.region_code = choice[2]

# 	def render(self, name=None, value=None, attrs=None):
# 		"Render override to add the region code class"
# 		name = name or self.name
# 		value = value or self.value
# 		attrs = attrs or self.attrs
# 		return format_html('<div class="region {3}">{1} <label for="{0}">{2}</label></div>', self.attrs['id'], self.tag(), self.choice_label, self.region_code)


# class RegionFieldRenderer(forms.widgets.ChoiceFieldRenderer):
# 	choice_input_class = RegionChoiceInput

# 	def render(self):
# 		"""
# 		Outputs a <ul> for this set of choice fields.
# 		If an id was given to the field, it is applied to the <ul> (each
# 		item in the list will get an id of `$id_$i`).
# 		"""
# 		id_ = self.attrs.get('id', None)
# 		start_tag = format_html('<ul id="{0}">', id_) if id_ else '<ul>'
# 		output = [start_tag]
# 		for i, choice in enumerate(self.choices):
# 			choice_value, choice_label, code = choice
# 			if isinstance(choice_label, (tuple, list)):
# 				attrs_plus = self.attrs.copy()
# 				if id_:
# 					attrs_plus['id'] += '_{0}'.format(i)
# 				sub_ul_renderer = RegionFieldRenderer(name=self.name, value=self.value, attrs=attrs_plus, choices=choice_label)
# 				sub_ul_renderer.choice_input_class = self.choice_input_class
# 				output.append(format_html('<li>{0}{1}</li>', choice_value, sub_ul_renderer.render()))
# 			else:
# 				w = self.choice_input_class(self.name, self.value,
# 											self.attrs.copy(), choice, i)
# 				output.append(format_html('<li>{0}</li>', force_text(w)))
# 		output.append('</ul>')
# 		return mark_safe('\n'.join(output))


# class Region(forms.CheckboxSelectMultiple):
# 	renderer = RegionFieldRenderer


class Sortable(forms.HiddenInput):

	class Media:
		css = {'all': ('syferadmin/libs/jquery-ui/jquery-ui.css', 'syferadmin/css/library-select.css',)}
		js = ('syferadmin/libs/jquery-ui/jquery-ui.js', 'syferadmin/js/library-select.js',)


class SortedSelectMultiple(forms.widgets.SelectMultiple):
	"""
	Override SelectMultiple to render selected options first
	"""

	def render_options(self, choices, selected_choices):
		# Filter out selected choices
		filtered = [c for c in self.choices if c[0] not in selected_choices]

		# Get selected choices in correct order
		selected = [c for c in self.choices if c[0] in selected_choices]
		selected = sorted(selected, key=lambda x: selected_choices.index(x[0]) if x[0] in selected_choices else 9999)

		# Update choices with selected in front
		self.choices = selected + filtered
		return super(SortedSelectMultiple, self).render_options(choices, selected_choices)


class Uploader(forms.Widget):
	"General file uploader widget"

	default_options = {
		# Enabling deletion and setting endpoint
		"deleteFile": {
			"enabled": True,
			"endpoint": "/admin/uploader/delete"
		},
		# Setting endpoint and overriding default parameter names to be more generic
		"request": {
			"endpoint": "/admin/uploader/add/",
			"inputName": "file",
			"uuidName": "uuid"
		},
		# Basic client-side file validation
		"validation": {
			"acceptFiles": "image/*",
			"allowedExtensions": ["jpg", "png", "gif", "jpeg"],
			"itemLimit": 100,
			"sizeLimit": pow(1024, 2) * 10
		},
		"uploaderType": "basic",
		# Reverse direction of file uploading
		"reversed": False,
		"description": False,
	}

	class Media:
		css = {'all': ('syferadmin/css/upload-widget.css',)}
		js = ('syferadmin/libs/fineupload/jquery.fineuploader-3.9.1.min.js', 'syferadmin/js/upload-widget.js',)

	def __init__(self, max=100, reversed=False, attrs=None, description=False):
		super(Uploader, self).__init__(attrs)
		self.uploads = []
		self.options = deepcopy(self.default_options)
		self.options['validation']['itemLimit'] = self.max = max
		self.options['reversed'] = reversed
		self.options['description'] = description

	def contents(self, field_name):
		"Return current uploader contents as <li>'s"
		if not self.uploads:
			return ""
		items = []
		for upload in self.uploads:
			group = getattr(upload, 'group', None)
			description = ''
			if self.options['description']:
				description = "<input type='text' name='{1}_description' value='{5}' />"
			items.append(format_html("""
				<li>
					{0}
					<input type='hidden' name='{1}' value='{2}' />
					<span class="delete">Delete</span>
					<input type='hidden' name='{1}_group' value='{3}' />
					<a href="{4}" class="zoom">View Image</a>
					""" + description + """
				</li>""",
				mark_safe(upload.render()),
				field_name,
				str(upload),
				str('' if group in (None, 'None') else group),
				getattr(upload, 'url', '#'),
				getattr(upload, 'description', ''),
			))
		return "".join(items)

	@property
	def drop_zone(self):
		return "<div class='drop-area'><span>Drop files here</span></div>"

	def render(self, name, value, attrs=None, extra_content=''):
		"Render library widget"
		content_holder = "{6}<ul>{3}</ul>"
		content_holder = "{4}{5}" + content_holder if self.options['reversed'] else content_holder + "{4}{5}"
		return format_html("""
		<div class='uploader' data-options='{0}' data-name='{1}' data-value='{2}'>
			""" + content_holder + """
		</div>""",
			mark_safe(json.dumps(self.options)), name, value,
			mark_safe(self.contents(name)),
			mark_safe(self.drop_zone),
			mark_safe(self.upload_button),
			mark_safe(extra_content))

	@property
	def upload_button(self):
		upload_button_style = ' style="display: none;"' if self.max > 0 and len(self.uploads) >= self.max else ''
		return "<div class='upload-button'%s>Upload File</div>" % upload_button_style

	def _has_changed(self, initial, data):
		"Override of Widget._has_changed to deal with deletions (empty string vs None)"
		return not initial == data


class VideoUploader(Uploader):
	"File upload for video files"

	def __init__(self, *args, **kwargs):
		super(VideoUploader, self).__init__(*args, **kwargs)
		self.options['validation']['acceptFiles'] = "video/mp4,video/x-m4v,video/*"
		self.options['validation']['allowedExtensions'] = ["mp4"]
		self.options['validation']['sizeLimit'] = pow(1024, 2) * 30

	def render(self, *args, **kwargs):
		kwargs['extra_content'] = "<p><small>Note: Uploader only accepts {} with a max size of {}MB.</small></p>".format(", ".join(self.options['validation']['allowedExtensions']), self.options['validation']['sizeLimit'] / pow(1024, 2))
		return super(VideoUploader, self).render(*args, **kwargs)
