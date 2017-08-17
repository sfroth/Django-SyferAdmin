import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
	help = 'Remove old report export files'

	def handle(self, *args, **options):
		directory = os.path.join(settings.MEDIA_ROOT, 'export')
		if os.path.exists(directory):
			now = time.time()
			for f in os.listdir(directory):
				file_path = os.path.join(directory, f)
				if os.stat(file_path).st_mtime < now - 3600:
					if os.path.isfile(file_path):
						os.remove(file_path)
