# Root-level Dockerfile for hosts (e.g. Render) that build from the repo root.
# docker-compose uses backend/Dockerfile instead; both build the same API.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
RUN useradd -m app && chown -R app /app
USER app
EXPOSE 8000
# RUN_SEED=1 loads demo data on start (safe to repeat). Hosts like Render provide $PORT.
CMD ["sh", "-c", "alembic upgrade head && if [ \"$RUN_SEED\" = \"1\" ]; then python -m app.seed; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
