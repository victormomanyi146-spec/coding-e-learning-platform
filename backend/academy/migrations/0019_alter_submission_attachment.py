from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academy", "0018_submission_attachment_submission_github_url_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="attachment",
            field=models.FileField(
                blank=True,
                help_text="Optional supporting file for an assignment/lab submission.",
                null=True,
                upload_to="submissions/",
                validators=[
                    FileExtensionValidator(
                        allowed_extensions=[
                            "pdf",
                            "doc",
                            "docx",
                            "txt",
                            "zip",
                            "py",
                            "ipynb",
                            "png",
                            "jpg",
                            "jpeg",
                        ]
                    )
                ],
            ),
        ),
    ]
