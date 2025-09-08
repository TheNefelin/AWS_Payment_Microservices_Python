# Dockerfile para transaction_microservice
FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno para optimización de Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update
RUN apt-get install -y gcc libpq-dev
RUN rm -rf /var/lib/apt/lists/*

# Copiar archivos de requerimientos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
