# Generated by Django 4.2.1 on 2023-07-06 08:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_alter_msg_options_msg_file_msg_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='msg',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='uploads/'),
        ),
        migrations.AlterField(
            model_name='msg',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/'),
        ),
    ]