# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('representatives', '0016_chamber_migrate_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mandate',
            name='role',
            field=models.CharField(default=b'', help_text=b'Eg.: president of a political group', max_length=255, blank=True),
        ),
    ]
