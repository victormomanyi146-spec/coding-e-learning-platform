# Coding E-Learning Platform

A web-based coding e-learning and assessment platform.

## Learning Cycle

Learn → Practice → Submit → Assess → Improve → Progress

## User Roles

- Student
- Instructor
- Administrator

## Local setup

From `backend/`:

```powershell
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata academy_content.json
python manage.py runserver
```

The local application runs at `http://127.0.0.1:8000/`.

Run the test suite with:

```powershell
python manage.py test academy
```
