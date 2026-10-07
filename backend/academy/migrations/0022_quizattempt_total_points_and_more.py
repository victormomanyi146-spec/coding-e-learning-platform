from django.db import migrations, models
from django.db.models import Sum


def snapshot_quiz_attempt_totals(apps, schema_editor):
    QuizAttempt = apps.get_model("academy", "QuizAttempt")
    QuizQuestion = apps.get_model("academy", "QuizQuestion")

    for attempt in QuizAttempt.objects.all().iterator():
        current_total = (
            QuizQuestion.objects
            .filter(
                quiz_id=attempt.quiz_id,
                is_active=True,
            )
            .aggregate(total=Sum("points"))["total"]
            or 0
        )

        score = attempt.score or 0
        snapshot_total = max(current_total, score)

        QuizAttempt.objects.filter(pk=attempt.pk).update(
            total_points=snapshot_total
        )


class Migration(migrations.Migration):

    dependencies = [
        ("academy", "0021_certificate"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizattempt",
            name="total_points",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(
            snapshot_quiz_attempt_totals,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="quizattempt",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(score__isnull=True)
                    | models.Q(score__lte=models.F("total_points"))
                ),
                name="quiz_attempt_score_lte_total_points",
            ),
        ),
    ]