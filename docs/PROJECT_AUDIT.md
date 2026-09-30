# Project Audit — Coding E-Learning Platform

## Baseline reviewed

The uploaded archive contained multiple generations of the project flattened
into the ZIP root. The latest generation was identified by its current Django
models/views/tests, migration 0018, shared navigation, quiz management and
45-test Assignment/Lab implementation.

## Adjustments made

1. Reconstructed the project into a normal Django directory structure.
2. Removed stale backup source files and duplicate historical project copies
   from the deliverable.
3. Removed the empty legacy `learning` app and unused duplicate quiz template.
4. Fixed `CourseAdmin.search_fields` to use the actual `instructor` CharField.
5. Added safe attachment extensions and a 10 MB upload limit.
6. Added an authenticated submission-attachment endpoint so only the
   submitting student or an instructor/admin can access an uploaded file.
7. Added direct quiz-route authentication, enrollment and sequencing checks.
8. Removed the duplicate quiz scoring form from the activity page; quiz taking
   now uses the dedicated quiz route.
9. Added migration 0019 for attachment validation.
10. Updated `academy_content.json` and `production_courses.json` to reflect the
    current course/quiz content (44 fixture objects).
11. Added production secret-key enforcement when `DJANGO_DEBUG=False`.
12. Added an explicit Africa/Nairobi timezone to Render configuration.
13. Changed the Render build command to `bash build.sh`.
14. Added media/upload and deployment notes.
15. Standardized login/register navigation and corrected visible character
    encoding issues.
16. Expanded regression tests to cover Assignment/Lab submissions,
    attachments, grading, attachment access control and direct quiz access.

## Verification performed

- Python syntax validation: passed for active source files.
- Template URL reference scan: no missing named URLs.
- Fixture validation: valid JSON; 44 academy content objects.
- Current uploaded database inspection: 3 courses, 1 module, 4 lessons,
  10 activities, 1 quiz, 5 quiz questions, 20 choices.
- The uploaded local project had previously established 45/45 Django tests
  passing before this audit. The adjusted test suite contains 51 test methods
  and should be run in the project's Windows virtual environment before use.

## Production considerations

The online Python code runner remains intentionally disabled when
`DJANGO_DEBUG=False`. Public code execution should be moved to an isolated
sandbox before enabling it in production.

Assignment/Lab attachments currently use Django filesystem storage. For a
durable Render deployment, configure S3-compatible or another persistent
object storage before treating uploaded files as permanent records.
