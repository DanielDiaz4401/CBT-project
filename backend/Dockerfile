# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# 1. Dependencias del sistema necesarias para compilar librerías de C
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Copiar requerimientos y crear "Wheels" (paquetes precompilados)
COPY src/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


# ==========================================
# STAGE 2: RUNNER (Producción)
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# 1. Instalar SOLO las librerías de sistema en tiempo de ejecución
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 2. Copiar los wheels ya compilados desde el builder e instalarlos
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# 3. Copiar el código fuente (CORREGIDO)
# Copiamos todo lo que hay dentro de 'src' a la carpeta '/app/app' del contenedor
COPY src/ /app/app/

# 4. Seguridad: Crear y usar un usuario sin privilegios de root
RUN useradd -m cbtuser && chown -R cbtuser:cbtuser /app
USER cbtuser

# 5. Variables de entorno por defecto
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# 6. Comando de ejecución (CORREGIDO)
# Como hemos metido todo en /app/app, el módulo a ejecutar es app.main
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]