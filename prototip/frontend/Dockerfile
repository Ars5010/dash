FROM node:18-alpine

WORKDIR /app

# Копирование package.json и установка зависимостей
COPY package.json .
RUN npm install

# Копирование исходного кода
COPY . .

# Открытие порта
EXPOSE 3000

# Команда запуска
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

