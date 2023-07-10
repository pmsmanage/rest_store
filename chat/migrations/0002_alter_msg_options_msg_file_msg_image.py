# Generated by Django 4.2.1 on 2023-07-06 08:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='msg',
            options={'ordering': ['-time_sent']},
        ),
        migrations.AddField(
            model_name='msg',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='data/files'),
        ),
        migrations.AddField(
            model_name='msg',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='data/images'),
        ),
    ]
