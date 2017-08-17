import csv

from django.utils.encoding import force_text


class UnicodeWriter:
	"""
	A CSV writer which will write rows to CSV file "f",
	which is encoded in the given encoding.
	"""

	def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwargs):
		self.writer = csv.writer(f, dialect=dialect, **kwargs)
		self.encoding = encoding

	def writerow(self, row):
		self.writer.writerow([force_text(s) for s in row])

	def writerows(self, rows):
		for row in rows:
			self.writerow(row)
