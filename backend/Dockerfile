FROM python:3.13-slim-bookworm

# Variables de entorno para optimizar Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Lima \
    LANG=es_PE.UTF-8 \
    LANGUAGE=es_PE:es \
    LC_ALL=es_PE.UTF-8 \
    LC_TIME=es_PE.UTF-8

# Directorio de trabajo
WORKDIR /backend

# Instalar dependencias del sistema y configurar locale/timezone en una sola capa
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        locales \
        tzdata \
    && echo "es_PE.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=es_PE.UTF-8 \
    && echo "$TZ" > /etc/timezone \
    && ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime \
    && apt-get purge -y --auto-remove build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Copiar solo los archivos de dependencias primero (cache más eficiente)
COPY pyproject.toml uv.lock ./

# Instalar dependencias Python con uv
RUN uv pip install --system --no-cache .

# Copiar código fuente
COPY auth_google/ ./auth_google/
COPY gmail/ ./gmail/
COPY database.py config.py main.py models.py __init__.py ./

# Crear usuario no-root y cambiar permisos
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /backend
USER appuser

# Exponer puerto
EXPOSE 8080

# Comando por defecto
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]