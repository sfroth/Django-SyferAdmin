import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
	help = 'Reduce the amount of dirs under cache buckets. Run this with --chars and update SYFERADMIN_IMAGE_DIR_SPLIT to the same value.'

	def add_arguments(self, parser):
		parser.add_argument('--chars',
			action='store',
			dest='chars',
			default=None,
			help='Number of characters to split the folder path by')

	def handle(self, *args, **options):
		if not options['chars']:
			raise CommandError('Please provide number of characters to split on!')

		directory = os.path.join(settings.MEDIA_ROOT, settings.IMAGEKIT_CACHEFILE_DIR)
		split = int(options['chars'])
		if os.path.exists(directory):
			# Find all cache folders
			for b in os.listdir(directory):
				b = os.path.join(directory, b)
				if os.path.isdir(b):
					# Find each cache folder
					for f in os.listdir(b):
						current_dir = os.path.join(directory, b, f)
						if len(f) > split and os.path.isdir(current_dir):
							fileparts = [directory, b]

							# Grab the first x characters of the filename as another directory
							fileparts.append(f[:split])
							fileparts.append(f)
							new_dir = os.path.join(*fileparts)

							try:
								shutil.copytree(current_dir, new_dir)
								print('Copying {} to {}'.format(current_dir, new_dir))
							except FileExistsError:
								pass
