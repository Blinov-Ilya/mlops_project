FROM python:3.11-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

FROM base AS api
COPY requirements/api.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py .
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
COPY requirements/worker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY data/ data/
COPY train.py worker.py ./
RUN python train.py
CMD ["python", "worker.py"]

FROM base AS ui
COPY requirements/ui.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY ui.py .
CMD ["streamlit", "run", "ui.py", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]

FROM base AS dagster
COPY requirements/dagster.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY etl.py .
RUN mkdir /dagster
CMD ["dagster", "dev", "-f", "etl.py", "-h", "0.0.0.0", "-p", "3000"]
