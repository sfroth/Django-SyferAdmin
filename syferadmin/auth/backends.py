import imaplib

from syferadmin.utils import user_factory


class BaseIMAPBackend(object):
	"""
	Authenticate against IMAP
	"""
	url = None
	qualified_email = None
	is_staff = False
	is_superuser = False

	def authenticate(self, username=None, password=None):
		username = username.strip()
		if not username.endswith(self.qualified_email):
			return None

		# Authenticate against imap
		M = imaplib.IMAP4_SSL(self.url)
		try:
			M.login(username, password)
		except imaplib.IMAP4.error:
			return None

		user, created = user_factory().objects.get_or_create(email=username)
		if created:
			user.name = username.replace(self.qualified_email, '').title()
		user.is_staff = self.is_staff
		user.is_superuser = self.is_superuser
		user.set_password(password)
		user.save()

		return user

	def get_user(self, user_id):
		try:
			return user_factory().objects.get(pk=user_id)
		except user_factory().DoesNotExist:
			return None
