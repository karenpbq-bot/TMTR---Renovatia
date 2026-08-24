# ============================================================================
# DOCKERFILE OPTIMIZADO PARA CONSULTORIO PSICOLÓGICO
# ============================================================================

FROM python:3.10-slim

# Evitar generación de archivos .pyc y activar salida sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias esenciales del sistema operativo
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar primero requirements.txt para optimizar la caché de capas de Docker
COPY requirements.txt /app/

# Instalar dependencias de Python sin caché para reducir el tamaño de la imagen
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación al contenedor
COPY . /app/

# Asegurar existencia del directorio de base de datos para la persistencia
RUN mkdir -p /app/database

# Exponer el puerto 5000 de Flask / Gunicorn
EXPOSE 5000

# Ejecutar script de inicialización de la BD y lanzar el servidor WSGI Gunicorn
CMD ["sh", "-c", "python init_db.py && gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 app:app"]
