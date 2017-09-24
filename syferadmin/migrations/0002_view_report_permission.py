# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


def add_permission(apps, schema_editor):
	content_type = ContentType.objects.get(app_label="syferadmin", model="user")
	permission = Permission.objects.create(codename='can_view_reports',
											name='Can view reports',
											content_type=content_type)


class Migration(migrations.Migration):

	dependencies = [
		('syferadmin', '0001_initial'),
	]

	operations = [
		migrations.RunPython(add_permission),
	]
