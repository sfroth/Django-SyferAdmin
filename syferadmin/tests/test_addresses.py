from django.test import TestCase

from ..mixins import AddressModel


class AddressTestCase(TestCase):
	addresses = (
		'15440 Laguna Canyon Road, Suite 220',
		'21831 Herencia',
		'900 N. Fonda ',
		'123 test',
		'1921 Maple Ave ',
		'24 Warner Ave ',
		'47768 Motor Lane ',
		'645 Los Altos Ave',
		'1921 Maple Ave Apt 8',
		'55 Little Rock Court ',
		'1912 Maple Ave Apt 9',
		'1 Main St ',
		'PO Box 333 ',
		'2201 chelsea road',
		'3602 Highland Dr.',
		'1895 Houghton dr',
		'434 W. Clearfork Dr.',
		'210 11Th Ave N, Apt 108',
		'23 Pacific Bay Circle #307',
		'1089 Lake Clarke Drive',
		'944 21st #C',
		'4259 Yosemite Way',
		'675 Lomita Drive',
		'P.O. 14619',
		'2700 Neilson Way Apt 824',
		'212 due east ',
		'4677 Orchard Avenue',
		'542 Burton Court',
		'5935 DARWIN COURT',
		'517 McCollum Cir',
		'1409 Onioni St.',
		'258 Kithcawan Rd',
		'31782 Isle Royal Drive',
		'512 Poinsett Rd.',
		'10600 4th Street N  #819',
		'2685 Bay Shore Dr',
		'219 Loma Avenue  Apt. #4',
		'1320 Crestview Ave',
		'474 Oak Street ',
		'5935 Linda Vista Rd',
		'5248 Ocean Breeze Ct',
		'24825 Guadalupe St.',
		'8712 N. 68th St. ',
		'33 wallys way unit 21',
		'4846 Kelly Dr.',
		'539 Fernwood Rd.',
		'323 Via de Vista',
		'718 10th Ave Apt C',
		'1300 bear creek parkway apt #1732',
		'41809 Corte Camara ',
		'1433 Superior Ave. Apt #286',
		'8520 NE Alderwood Rd Suite D #35573',
	)

	def test_address_lines_2(self):
		for street_address in self.addresses:
			address = AddressModel(address=street_address)
			lines = address.address_lines(2, 25)
			self.assertEqual(len(lines), 2)
			for line in lines:
				self.assertIn(line, address.address)

	def test_address_lines_3(self):
		for street_address in self.addresses:
			address = AddressModel(address=street_address)
			lines = address.address_lines(3, 30)
			self.assertEqual(len(lines), 3)
			for line in lines:
				self.assertIn(line, address.address)


class AddressPOBoxTestCase(TestCase):
	po_box_addresses = (
		'PO Box 333',
		'P.O. 14619',
		'P.O. Box 100',
		'P. O. Box 100',
		'P0 Box',
		'Postal Office Box 100',
		'post office Box 100',
		'POB 100',
		'P.O.B. 100',
	)
	standard_addresses = (
		'12345 Port Orlando Drive',
		'123 Boxing Street',
		'34 Box Handler Road',
		'424 PO Dance drive',
		'234 P.O.D. Circle',
		'777 Post Oak Blvd',
		'123 box canyon rd',
		'Obere Kaiserstrasse 4',
		'Brandenburger Straße 12a',
	)

	def test_matches(self):
		for street_address in self.po_box_addresses:
			address = AddressModel(address=street_address)
			print(street_address)
			self.assertTrue(address.is_po_box)

	def test_misses(self):
		for street_address in self.standard_addresses:
			address = AddressModel(address=street_address)
			self.assertFalse(address.is_po_box)
