from django.db import migrations


class AddField(migrations.AddField):
	"""
	Allow adding a field to a model from a different application.

	This enables us to add tranlsation fields in the main app.
	"""

	def __init__(self, *args, **kwargs):
		self.app_label = kwargs.get('model_name').split('.')[0]
		kwargs['model_name'] = kwargs.get('model_name').split('.')[1]
		super(AddField, self).__init__(*args, **kwargs)

	def state_forwards(self, app_label, state):
		return super(AddField, self).state_forwards(self.app_label, state)

	def database_forwards(self, app_label, *args):
		return super(AddField, self).database_forwards(self.app_label, *args)

	def state_backwards(self, app_label, state):
		return super(AddField, self).state_backwards(self.app_label, state)

	def database_backwards(self, app_label, *args):
		return super(AddField, self).database_backwards(self.app_label, *args)


class AlterField(migrations.AlterField):
	"""
	Allow adding a field to a model from a different application.

	This enables us to add tranlsation fields in the main app.
	"""

	def __init__(self, *args, **kwargs):
		self.app_label = kwargs.get('model_name').split('.')[0]
		kwargs['model_name'] = kwargs.get('model_name').split('.')[1]
		super(AlterField, self).__init__(*args, **kwargs)

	def state_forwards(self, app_label, state):
		return super(AlterField, self).state_forwards(self.app_label, state)

	def database_forwards(self, app_label, *args):
		return super(AlterField, self).database_forwards(self.app_label, *args)

	def state_backwards(self, app_label, state):
		return super(AlterField, self).state_backwards(self.app_label, state)

	def database_backwards(self, app_label, *args):
		return super(AlterField, self).database_backwards(self.app_label, *args)


class RemoveField(migrations.RemoveField):
	"""
	Removes a field from a model.
	"""

	def __init__(self, *args, **kwargs):
		self.app_label = kwargs.get('model_name').split('.')[0]
		kwargs['model_name'] = kwargs.get('model_name').split('.')[1]
		super(RemoveField, self).__init__(*args, **kwargs)

	def state_forwards(self, app_label, state):
		return super(RemoveField, self).state_forwards(self.app_label, state)

	def database_forwards(self, app_label, *args):
		return super(RemoveField, self).database_forwards(self.app_label, *args)

	def state_backwards(self, app_label, state):
		return super(RemoveField, self).state_backwards(self.app_label, state)

	def database_backwards(self, app_label, *args):
		return super(RemoveField, self).database_backwards(self.app_label, *args)
