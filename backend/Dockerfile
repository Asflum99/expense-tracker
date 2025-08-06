FROM python:3.13-slim-bookworm

# Variables para optimizar Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /backend

# Instalar dependencias del sistema y configurar locale en una sola capa
RUN apt-get update && apt-get install -y \
    tzdata \
    build-essential \
    locales \
    && echo "es_PE.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=es_PE.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establecer locale
ENV LANG=es_PE.UTF-8
ENV LANGUAGE=es_PE:es
ENV LC_ALL=es_PE.UTF-8
ENV LC_TIME=es_PE.UTF-8

# Instalar dependencias Python (cacheado si requirements.txt no cambia)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Exponer puerto (documentación)
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]