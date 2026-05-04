FROM node:lts-slim
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src/ .
EXPOSE 4321
CMD ["npm", "run", "dev", "--", "--host"]