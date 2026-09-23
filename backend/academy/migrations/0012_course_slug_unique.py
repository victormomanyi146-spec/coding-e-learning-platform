from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academy", "0011_enrollment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
    ]
