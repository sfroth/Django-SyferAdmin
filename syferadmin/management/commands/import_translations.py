import codecs
from collections import namedtuple
import csv
from lxml import etree
import os
import re

from modeltranslation.translator import translator

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


IMPORT_FILE = 'tmp/model_translations.csv'


class Command(BaseCommand):
	args = '<iso_language_code> [<translation_file>]'
	help = 'Import Translation csv'
	ModelField = namedtuple('ModelField', ['model', 'field'])

	def add_arguments(self, parser):
		parser.add_argument('iso_language_code')
		parser.add_argument('translation_file')

	def handle(self, *args, **options):
		if len(args) == 0:
			self.stderr.write("Please enter a language code.")

		language_code = args[0]
		language_file = args[1] if len(args) > 1 else IMPORT_FILE

		stats = {'updated': 0, 'skipped': 0}
		model_field_lookup = {}

		_, file_extension = os.path.splitext(language_file)
		if file_extension == '.xml':
			doc = etree.parse(language_file)
			for el in doc.iter('record'):
				data = {'model': el.get('model'), 'row': el.get('row'), 'field': el.get('field'), 'text': el.text}
				self.import_record(data, language_code, model_field_lookup, stats)
		else:
			# load language csv file
			reader = csv.reader(codecs.open(language_file, 'r', 'utf-8'), dialect=csv.excel)
			fields = next(reader)  # Header row
			if fields[0].startswith(codecs.BOM_UTF8.decode(encoding='UTF-8')):
				fields[0] = fields[0][len(codecs.BOM_UTF8.decode(encoding='UTF-8')):]

			for row in reader:
				try:
					data = dict(zip(fields, row))
					self.import_record(data, language_code, model_field_lookup, stats)

				except Exception as e:
					print(e)
					self.stdout.write("Could not import translation record:")
					print(row)

		self.stdout.write("Import successful. Records updated: {}. Records skipped: {}.".format(stats['updated'], stats['skipped']))

	def import_record(self, row, language_code, model_field_lookup, stats):
		# Save the model/field/translation field lookups so we don't have to duplicate that logic for every field/record of each table
		if row['text'] == '':
			stats['skipped'] += 1
			return

		model_field = self.ModelField(model=row['model'], field=row['field'])
		if model_field in model_field_lookup:
			ct_class, field_name, translation_field, default_lang_field = model_field_lookup[model_field]
		else:
			content_type = row['model'].split('_', 1)
			ct = ContentType.objects.get(app_label=content_type[0], model=content_type[1])
			ct_class = ct.model_class()

			translation_info = translator.get_options_for_model(ct_class)
			field_name = row['field']
			# get untranslated field name if necessary.
			# I accidentally set this up so that it would send, e.g. title_en to the client, so we need to translate that to title
			if field_name not in translation_info.fields:
				for field in translation_info.fields:
					for lang in translation_info.fields[field]:
						if lang.column == field_name:
							field_name = field
							break
					if field_name != row['field']:
						break
			# if unable to grab untranslated field name, error this record
			if field_name not in translation_info.fields:
				raise AttributeError('Field {} not found'.format(field_name))

			# get translated field name for the current language and default language
			translation_field = ''
			default_lang_field = ''
			for lang in translation_info.fields[field_name]:
				if lang.column == '{}_{}'.format(field_name, language_code.replace('-', '_')):
					translation_field = lang.column
				elif lang.column == '{}_{}'.format(field_name, settings.MODELTRANSLATION_DEFAULT_LANGUAGE.replace('-', '_')):
					default_lang_field = lang.column
			if translation_field == '':
				raise AttributeError('Translation Field {} for {} not found'.format(field_name, language_code))
			if default_lang_field == '':
				raise AttributeError('Default Language Field for {} not found'.format(field_name))
			model_field_lookup[model_field] = (ct_class, field_name, translation_field, default_lang_field)

		obj = ct_class.objects.filter(pk=int(row['row'])).first()

		# Only save records where the translated value is different from the untranslated value (saved in default translation language or untranslated field)
		# Some records were being returned with text differing only by the number of line breaks. This shouldn't be treated as translated
		space_fix_text = re.sub("[\x00-\x20]+", " ", row['text'])
		if obj is None:
			stats['skipped'] += 1
		else:
			if getattr(obj, field_name) and (re.sub("[\x00-\x20]+", " ", getattr(obj, field_name)) == space_fix_text or re.sub("[\x00-\x20]+", " ", getattr(obj, default_lang_field)) == space_fix_text):
				stats['skipped'] += 1
			else:
				ct_class.objects.filter(pk=int(row['row'])).update(**{translation_field: row['text']})
				stats['updated'] += 1
