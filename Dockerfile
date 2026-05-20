# Fly.io / Render и другие хосты с Docker
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV PORT=8080

WORKDIR /app

# Runtime + *-dev для сборки pycairo (зависимость WeasyPrint) через pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libharfbuzz0b \
    libfontconfig1 \
    shared-mime-info \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip wheel \
  && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
