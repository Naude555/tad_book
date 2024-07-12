# Generated by Django 4.2.13 on 2024-07-08 09:20

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookings',
            name='create_datetime',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bookings',
            name='update_datetime',
            field=models.DateTimeField(auto_now=True),
        ),
    ]