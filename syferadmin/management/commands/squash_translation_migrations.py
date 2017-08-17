import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
	args = 'migration_file1.py migration_file2.py migration_file3.py'
	help = 'Merge translation migrations into one'
	arg_regex = re.compile('([a-z_]+)=\'([^\']+)\'', re.S | re.M)
	dep_regex = re.compile('dependencies = \[([^\]]+)\]', re.S | re.M)
	fld_regex = re.compile('AddField\((.+?)\s\)', re.S | re.M)

	def handle(self, *args, **options):
		self.stdout.write("""# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from syferadmin.operations import AddField


class Migration(migrations.Migration):

	dependencies = [""")
		for file in args:
			for dep in self.get_dependencies(file):
				self.stdout.write(dep)

		self.stdout.write("""\t]

	operations = [""")

		for file in args:
			self.stdout.write("\t# {sep} {app} {sep}\n".format(app=self.get_app(file), sep='-' * 15))
			for field in self.get_fields(file):
				self.stdout.write(field)

		self.stdout.write("\n\t]")

	def get_app(self, file):
		return file.split('/')[-3]

	def get_dependencies(self, file):
		with open(file, 'r') as f:
			for dep in self.dep_regex.finditer(f.read()):
				yield dep.group(1)

	def get_field_args(self, args):
		return {m.group(1): m.group(2) for m in self.arg_regex.finditer(args) if m}

	def get_fields(self, file):
		default_language = settings.LANGUAGE_CODE.replace('-', '_')
		app_name = self.get_app(file)
		updates = []
		with open(file, 'r') as f:
			for m in self.fld_regex.finditer(f.read()):
				args = self.get_field_args(m.group(1))
				if args.get('name') and args['name'].endswith(default_language):
					updates.append({
						'field': args['name'].replace('_{}'.format(default_language), ''),
						'model': args['model_name'],
					})
				yield """\tAddField({}),\n""".format(m.group(1).replace("model_name='", "model_name='{}.".format(app_name)))

		for u in updates:
			yield """\tmigrations.RunSQL("UPDATE {app_name}_{model} SET {field}_{language} = {field}", ""),\n""".format(app_name=app_name, language=default_language, **u)
