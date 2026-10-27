# Build context: repository root (the plugins/ and config/ folders are shipped with the API).
FROM python:3.12-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG PIP_INDEX_URL
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app backend/app
COPY backend/alembic.ini backend/alembic.ini
COPY backend/migrations backend/migrations
COPY plugins plugins
COPY config config

RUN useradd --system --uid 10001 ariane && mkdir -p /srv/backend/data && chown -R ariane /srv/backend/data
USER ariane
WORKDIR /srv/backend
ENV ARIANE_CUSTOMERS_CONFIG_PATH=/srv/config/customers.json PYTHONPATH=/srv

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/v1/health', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
