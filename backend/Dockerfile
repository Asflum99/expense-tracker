FROM python:3.13-slim-bookworm

# Variables para optimizar Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /backend

RUN apt-get update && apt-get install -y tzdata \
    build-essential \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generar e instalar el locale es_PE.UTF-8
RUN echo "es_PE.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=es_PE.UTF-8

# Establecer el locale en las variables de entorno
ENV LANG=es_PE.UTF-8  
ENV LANGUAGE=es_PE:es  
ENV LC_ALL=es_PE.UTF-8

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]