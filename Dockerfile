# Используем базовый образ Python 3.9
FROM python:3.9

# Устанавливаем переменную среды для запуска в неинтерактивном режиме
ENV PYTHONUNBUFFERED 1

# Установка необходимых зависимостей
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем requirements.txt в контейнер
COPY requirements.txt /app/

# Устанавливаем зависимости приложения
RUN pip install -r requirements.txt

# Копируем все файлы проекта в контейнер
COPY . /app/

# Запускаем FastAPI приложение
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
