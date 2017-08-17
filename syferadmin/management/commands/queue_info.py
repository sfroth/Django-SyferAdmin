from datetime import datetime, timedelta
from time import time

from django.core.management.base import BaseCommand

from celery import current_app
import kombu.five


class Command(BaseCommand):
	help = 'Show Celery Queue Info'

	def elapsed(self, task):
		if task['time_start']:
			return str(datetime.now() - datetime.fromtimestamp(time() - (kombu.five.monotonic() - task['time_start']))).split('.')[0]
		return str(timedelta(seconds=0))

	def handle(self, *args, **options):
		i = current_app.control.inspect()
		print('| {:10} | {:25} | {:36} | {:40} | {:7} |'.format('Status', 'Host', 'ID', 'Task', 'Elapsed'))
		for m in ['active', 'reserved', 'scheduled']:
			self.method(getattr(i, m))

	def method(self, callable):
		queue = callable()
		if queue:
			for host in queue:
				for task in queue[host]:
					print('| {status:10} | {host:25} | {task[id]:36} | {task[name]:40} | {elapsed:>7} |'.format(status=callable.__name__, task=task, elapsed=self.elapsed(task), host=host))
