# Dockerfile for Django + Gunicorn + PostGIS client libs
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    binutils \
    libproj-dev \
    proj-bin \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# Collect static and run migrations handled by entrypoint/commands
CMD ["gunicorn", "retam.wsgi:application", "--bind", "0.0.0.0:8000"]
