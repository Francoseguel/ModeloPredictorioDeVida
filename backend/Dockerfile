# --- Etapa 1: Constructor (Builder) ---
# Usamos una imagen base ligera para compilar dependencias
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalamos dependencias del sistema necesarias para compilar librerías de ML
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Creamos un entorno virtual para aislar las dependencias limpiamente
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiamos solo el requirements para aprovechar la caché de Docker
COPY requirements.txt .

# Instalamos las dependencias limpiando la caché de pip (Rúbrica: Limpieza de capas)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Etapa 2: Producción (Runner) ---
# Empezamos desde una imagen limpia
FROM python:3.11-slim

WORKDIR /app

# Copiamos únicamente el entorno virtual ya compilado de la etapa anterior (Rúbrica: Multi-stage build)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Rúbrica: Configurar un usuario sin privilegios (no root)
RUN adduser --disabled-password --gecos '' mluser

# Copiamos el código fuente de la API y el modelo (.joblib)
COPY . .

# Otorgamos propiedad de los archivos al nuevo usuario y creamos una carpeta para persistencia
RUN mkdir -p /app/data && chown -R mluser:mluser /app

# Cambiamos al usuario sin privilegios para ejecutar la aplicación
USER mluser

# Documentamos el puerto expuesto
EXPOSE 8000

# Comando para levantar FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]