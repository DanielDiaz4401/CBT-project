FROM node:20-alpine

WORKDIR /app

# Instalar dependencias
COPY src/package.json src/package-lock.json* ./
RUN npm install

# Copiar el resto del código
COPY src/ .

EXPOSE 4321
ENV HOST=0.0.0.0

# Arrancamos en modo desarrollo nativo
CMD ["npm", "run", "dev", "--", "--host"]