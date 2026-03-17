# JamieDate Backend

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust, enterprise-grade backend system built with Django, designed for real-time messaging, automated chatbot interactions, and multi-platform social media integration (Facebook, Instagram, WhatsApp).

---

## 🚀 Key Features

-   **Real-time Communication:** Powered by Django Channels and WebSockets for instantaneous dashboard updates.
-   **Multi-Platform Integration:** seamless connection with Meta Graph API for managing conversations across Facebook, Instagram, and WhatsApp.
-   **AI-Powered Chatbot:** Asynchronous chatbot processing using Celery and Redis to ensure high performance and non-blocking I/O.
-   **Advanced User Management:** Custom user models with role-based access control (Admin/Tester) and secure JWT authentication.
-   **Automated Lead Scoring:** Intelligent tracking of user interactions with dynamic status and progress scoring.
-   **Scalable Architecture:** Built following industry best practices with clean service layers and asynchronous task management.

---

## 🛠 Tech Stack

-   **Backend:** Django 6.0, Django REST Framework (DRF)
-   **Real-time:** Django Channels, Daphne
-   **Asynchronous Tasks:** Celery, Redis
-   **Authentication:** SimpleJWT (JSON Web Tokens)
-   **Database:** SQLite (Development) / PostgreSQL (Recommended for Production)
-   **API Documentation:** Swagger/OpenAPI (drf-yasg)
-   **Server:** Nginx, Gunicorn/Daphne

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Redis Server (for Celery and Channels)
- Virtual Environment

### Setup Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/jamiedate-backend.git
    cd jamiedate-backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory and add the following:
    ```env
    SECRET_KEY=your_secret_key
    DEBUG=True
    CELERY_BROKER_URL=redis://localhost:6379/0
    FB_PAGE_ACCESS_TOKEN=your_token
    FB_VERIFY_TOKEN=your_verify_token
    CHATBOT_URL=your_chatbot_api_url
    ```

5.  **Run Migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Create Superuser:**
    ```bash
    python manage.py createsuperuser
    ```

---

## 🏃 Running the Application

### 1. Start the Development Server (Daphne for WebSockets)
```bash
daphne -b 0.0.0.0 -p 8000 JamieDate.asgi:application
```

### 2. Start Celery Worker (New Terminal)
```bash
# Windows
celery -A JamieDate worker --loglevel=info -P gevent
# Linux/Mac
celery -A JamieDate worker --loglevel=info
```

---

## 📖 API Documentation
Once the server is running, you can access the interactive API documentation at:
-   **Swagger UI:** `http://localhost:8000/swagger/`
-   **Redoc:** `http://localhost:8000/redoc/`


---

## 📄 License

Copyright (c) 2026 FireAI agency. All Rights Reserved.

This is proprietary software. Unauthorized copying, distribution, or use of this code, via any medium, is strictly prohibited. Access is restricted to authorized users only.

Built with passion by [Arif](https://github.com/Aru-01)
