import os

from django.conf import settings
from django.db import models
from imagekit.cachefiles import ImageCacheFile

from ..widgets import Uploader
from ..uploader.helpers import UploadedFile, UploadThumbSpec
from . import form_fields
from ..validators import RelativeURLValidator


class ImageFieldFile(models.fields.files.ImageFieldFile):

	def render(self):
		"Render in uploader context"
		thumb = ImageCacheFile(UploadThumbSpec(source=self))
		try:
			return '<img src="{}" />'.format(thumb.url)
		except IOError:
			return "Source not found"


class ImageUploaderField(models.ImageField):
	"""Image Field for custom Uploader"""
	widget = Uploader
	attr_class = ImageFieldFile

	def clean(self, data, initial=None):
		if len(data) == 1:
			if not UploadedFile.create(data[0]).valid():
				return data[0]
		return None


class VideoFieldFile(models.fields.files.FieldFile):
	encode_formats = ['webm', 'ogv', 'mp4']

	def delete(self, save=True):
		"Delete other versions of this video, including frame jpg"
		for version in self.versions(None, True):
			self.storage.delete(version['path'])
		super().delete(save)

	def frame(self, path=None):
		"Get video frame jpg"
		path = path or self.name
		filename = os.path.basename(path)
		basename = filename.split('.')[0]
		extension = 'jpg'
		version_filename = '{}-frame.{}'.format(basename, extension)
		return ImageFieldFile(self.instance, self.field, path.replace(filename, version_filename))

	def render(self):
		try:
			thumb = ImageCacheFile(UploadThumbSpec(source=self.frame()))
			return '<img src="{}" />'.format(thumb.url)
		except IOError:
			return "Source not found"

	def save(self, name, content, save=True):
		"Save additional encodings and thumbs"
		super().save(name, content, save=False)
		versions = zip(self.versions(name, True), self.versions(None, True))
		for old_version, new_version in versions:
			self.storage.save(new_version['path'], open(old_version['path'], 'rb'))
		if save:
			self.instance.save()

	def versions(self, path=None, include_frame=False):
		"Return different encoded versions for this video"
		path = path or self.name
		filename = os.path.basename(path)
		modified_time = os.path.getmtime(os.path.join(settings.MEDIA_ROOT, path))
		basename = filename.split('.')[0]
		for extension in self.encode_formats:
			version_filename = '{}-encoded.{}'.format(basename, extension)
			yield {
				'path': path.replace(filename, version_filename),
				'url': self.url.replace(filename, '{}?{}'.format(version_filename, modified_time)),
				'file_name': version_filename,
				'mime_type': 'video/{}'.format(extension),
			}
		if include_frame:
			extension = 'jpg'
			version_filename = '{}-frame.{}'.format(basename, extension)
			yield {
				'path': path.replace(filename, version_filename),
				'url': self.url.replace(filename, '{}?{}'.format(version_filename, modified_time)),
				'file_name': version_filename,
				'mime_type': 'image/{}'.format(extension),
			}


class VideoUploaderField(models.FileField):
	"""Video Field for custom Uploader"""
	widget = Uploader
	attr_class = VideoFieldFile

	def clean(self, data, initial=None):
		if len(data) == 1:
			if not UploadedFile.create(data[0]).valid():
				return data[0]
		return None


class RegionField(models.ManyToManyField):
	"Standard region field"

	def __init__(self, *args, **kwargs):
		kwargs['to'] = 'syferadmin.Region'
		super().__init__(*args, **kwargs)

	def formfield(self, **kwargs):
		kwargs.setdefault('form_class', form_fields.RegionField)
		return super().formfield(**kwargs)


class RelativeURLField(models.CharField):
	default_validators = [RelativeURLValidator()]
	description = "URL"

	def __init__(self, verbose_name=None, name=None, **kwargs):
		kwargs['max_length'] = kwargs.get('max_length', 200)
		super().__init__(verbose_name, name, **kwargs)

	def deconstruct(self):
		name, path, args, kwargs = super().deconstruct()
		if kwargs.get("max_length") == 200:
			del kwargs['max_length']
		return name, path, args, kwargs

	def formfield(self, **kwargs):
		# As with CharField, this will cause URL validation to be performed
		# twice.
		defaults = {
			'form_class': form_fields.RelativeURLField,
		}
		defaults.update(kwargs)
		return super().formfield(**defaults)


class TreeForeignKey(models.ForeignKey):
	"Override MPTT TreeForeignKey"

	def formfield(self, **kwargs):
		kwargs.setdefault('form_class', form_fields.TreeNodeChoiceField)
		return super().formfield(**kwargs)


class TreeManyToManyField(models.ManyToManyField):
	"Override MPTT TreeManyToManyField"

	def formfield(self, **kwargs):
		kwargs.setdefault('form_class', form_fields.TreeNodeMultipleChoiceField)
		return super().formfield(**kwargs)
