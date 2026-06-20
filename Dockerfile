# Multi-stage build for the Service Desk app.
FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Collect static so WhiteNoise can serve hashed assets at runtime.
# A throwaway key is fine here — collectstatic touches no secrets or DB.
RUN SECRET_KEY=build DEBUG=false python manage.py collectstatic --no-input

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
