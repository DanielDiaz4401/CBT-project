# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app

# 1. Instalar dependencias
COPY src/package.json src/package-lock.json* ./
RUN npm ci

# 2. Copiar código y generar el build estático de Astro
COPY src/ .
RUN npm run build


# ==========================================
# STAGE 2: RUNNER (NGINX)
# ==========================================
FROM nginx:alpine

# 1. Copiar los archivos estáticos generados en la etapa anterior a la carpeta pública de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 2. Exponer el puerto por defecto de Nginx
EXPOSE 80

# 3. Arrancar Nginx en primer plano
CMD ["nginx", "-g", "daemon off;"]