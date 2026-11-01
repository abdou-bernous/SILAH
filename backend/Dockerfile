# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary needs libpq at runtime; build tools stay out of the final layer
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 appuser && mkdir -p /app/media && chown -R appuser:appuser /app
USER appuser

# Real value comes from the platform env at runtime; placeholder only lets
# collectstatic run at build time without touching the database.
RUN SECRET_KEY=build-time-placeholder-not-used-at-runtime \
    python manage.py collectstatic --noinput

EXPOSE 8000

# SEED_DEMO=1 fills an empty database with the fictional demo company.
CMD ["sh", "-c", "python manage.py migrate --noinput && if [ \"$SEED_DEMO\" = \"1\" ]; then python manage.py seed_demo; fi && gunicorn silah.wsgi --bind 0.0.0.0:${PORT:-8000}"]
