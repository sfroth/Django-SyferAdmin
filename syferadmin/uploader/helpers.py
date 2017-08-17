import os

from django.core.files.base import File
from django.conf import settings
from imagekit import ImageSpec
from imagekit.cachefiles import ImageCacheFile
from imagekit.processors import ResizeToFill

from syferadmin import video
from syferadmin.utils import register_specs
from syferadmin.tasks import encode_video


class UploadThumbSpec(ImageSpec):
	processors = [ResizeToFill(128, 128)]
	format = 'png'

register_specs([
	('syferadmin:uploadthumb', UploadThumbSpec),
])


class UploadedFile(object):
	"Wrapper for a file uploaded via the uploader"
	prefix = 'sa-upload-'
	transfer_dir = settings.FILE_UPLOAD_TEMP_DIR
	thumbs_dir = 'CACHE/upload-thumbs'
	file_type = 'file'

	@classmethod
	def create(cls, uuid, file_obj=None):
		file_name = file_obj.name if file_obj else uuid
		extension = os.path.splitext(file_name)[1].lower()[1:]
		for subclass in [UploadedImage, UploadedVideo]:
			if extension in subclass.extensions:
				return subclass(uuid, file_obj)
		return cls(uuid, file_obj)

	def __init__(self, uuid, file_obj=None):
		self.uuid = uuid
		self.file = None
		self.thumb = None
		if file_obj:
			self.file = file_obj
			self.uuid += os.path.splitext(self.file.name)[1].lower()
		self.name = self.prefix + self.uuid
		self.path = os.path.join(self.transfer_dir, self.name)

	def generate_thumb(self):
		pass

	def exists(self):
		return os.path.exists(self.path)

	def remove(self):
		os.remove(self.path)

	def save(self):
		"Save to temporary location"
		with open(self.path, 'w+b') as destination:
			for chunk in self.file.chunks():
				destination.write(chunk)
		self.generate_thumb()

	def to_file(self):
		return File(open(self.path, 'rb'))

	def valid(self):
		if self.file:
			return True
		return os.path.exists(self.path)


class UploadedImage(UploadedFile):
	extensions = ['gif', 'jpg', 'jpeg', 'png']
	file_type = 'image'

	def generate_thumb(self):
		"Create thumbnail"
		self.thumb = ImageCacheFile(UploadThumbSpec(source=self.file), name=os.path.join(self.thumbs_dir, self.uuid))
		self.thumb.generate()


class UploadedVideo(UploadedFile):
	extensions = ['mp4']
	encode_formats = ['mp4', 'ogv', 'webm']
	file_type = 'video'

	def encoded_files(self):
		basename, _ = os.path.splitext(self.name)
		for file_type in self.encode_formats:
			yield os.path.join(self.transfer_dir, '{}-encoded{}'.format(basename, '.' + file_type))

	def generate_thumb(self):
		"Encode video(s) and create thumb on upload"
		video_file = open(self.path, 'rb')
		# Delegate video encoding to celery
		encode_video.delay(video_file.name, self.transfer_dir, self.encode_formats)
		frame_file = video.thumb(video_file.name, self.transfer_dir)
		self.thumb = ImageCacheFile(UploadThumbSpec(source=frame_file), name=os.path.join(self.thumbs_dir, self.uuid.replace('.mp4', '.jpg')))
		self.thumb.generate()

	def is_encoded(self):
		return all([os.path.exists(encoded) for encoded in self.encoded_files()])

	def remove(self):
		super(UploadedVideo, self).remove()
		for encoded in self.encoded_files():
			os.remove(encoded)
