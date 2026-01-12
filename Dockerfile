FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

WORKDIR /app

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем папку для временных файлов
RUN mkdir -p downloads && chmod 777 downloads

# Запуск через переменную PORT
CMD ["python", "main.py"]
