# Coding E-Learning Platform

A Django-based coding e-learning and assessment platform.

## Learning cycle

**Learn -> Practice -> Submit -> Assess -> Improve -> Progress**

## Current features

- Course catalogue
- Course -> Module -> Lesson -> Activity structure
- Student activity completion tracking
- Python coding editor with program input
- Submission history
- Instructor submission review and grading
- Course progress dashboard
- Django REST Framework student login/profile API
- Django admin management

## Project structure

```text
Coding E-Learning Platform/
└── backend/
    ├── academy/
    ├── accounts/
    ├── config/
    ├── static/
    ├── templates/
    ├── db.sqlite3
    ├── manage.py
    └── requirements.txt
```

## Setup on Windows PowerShell

```powershell
cd "D:\Resume Projects\Coding E-Learning Platformackend"

python -m venv venv
.env\Scripts\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

Open:

`http://127.0.0.1:8000/`

Courses:

`http://127.0.0.1:8000/courses/`

Admin:

`http://127.0.0.1:8000/admin/`

## Important security note

The coding activity runner executes Python code on the machine running Django. It is suitable for **local development/testing only**.

Before deploying this feature publicly, move code execution into an isolated sandbox/container with strict CPU, memory, filesystem, network, and process limits. Never execute untrusted student code directly on the production web server.

## Environment variables

For deployment, configure:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=your-domain.example`
- `DJANGO_TIME_ZONE=Africa/Nairobi`

Do not commit production secrets or a production database to source control.
