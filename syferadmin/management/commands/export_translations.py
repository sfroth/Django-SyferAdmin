import os
from lxml import etree

from modeltranslation.translator import translator

from django.conf import settings
from django.core.management.base import BaseCommand

EXPORT_FILE = 'tmp/model_translations.csv'


class Command(BaseCommand):
	args = '<iso_language_code> [<translation_file>] [include_defaults]'
	help = 'Export Translations to file'

	def handle(self, *args, **options):
		if len(args) == 0:
			self.stderr.write("Please enter a language code.")

		language_code = args[0]
		language_file = args[1] if len(args) > 1 else EXPORT_FILE
		include_defaults = args[2] == 'true' if len(args) > 2 else False

		stats = {'exported': 0}
		fields = ['model', 'row', 'field', 'text']
		data = []  # {'model': , 'row': , 'field': , 'text': }
		models = translator.get_registered_models()
		for model in models:
			table_name = model._meta.db_table
			translation_info = translator.get_options_for_model(model)
			for record in model.objects.all():
				for field in translation_info.fields:
					# exclude EAV values that aren't text
					if table_name == 'eav_value' and record.attribute.datatype not in ('char', 'text'):
						continue
					value = ''
					default_value = ''
					for lang in translation_info.fields[field]:
						if lang.language == language_code:
							value = getattr(record, lang.column)
						elif lang.language == settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
							default_value = getattr(record, lang.column)
					if not value and include_defaults:
						value = default_value
					if not value:  # exclude empty records
						continue
					# Exclude Meta values that aren't text
					if table_name == 'syferadmin_meta' and value in ('True', 'False', 'None'):
						continue
					data.append({'model': table_name, 'row': record.pk, 'field': field, 'text': value})
					stats['exported'] += 1

		_, file_extension = os.path.splitext(language_file)
		if file_extension == '.xml':
			root = etree.Element('translations')
			for record in data:
				node = etree.SubElement(root, 'record')
				node.text = etree.CDATA(record['text'])
				node.attrib['model'] = record['model']
				node.attrib['row'] = str(record['row'])
				node.attrib['field'] = record['field']
			etree.ElementTree(root).write(language_file, pretty_print=True, encoding="UTF-8")
		else:  # csv
			from syferadmin.csv import UnicodeWriter
			import codecs
			with codecs.open(language_file, "w", 'utf-8') as fp:
				fp.write(codecs.BOM_UTF8.decode(encoding='UTF-8'))  # this is necessary to get Excel to recognize a UTF-8 file
				writer = UnicodeWriter(fp)

				writer.writerow([i.encode('utf-8') for i in fields])

				for record in data:
					row = []
					for field in fields:
						row.append(record[field])
					writer.writerow(row)

		self.stdout.write("Export successful. Records exported: {}.".format(stats['exported']))
