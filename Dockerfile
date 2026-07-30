# Лёгкий образ только для прогона тестов — не для продакшена.
FROM python:3.12-slim

WORKDIR /app

# Сначала только requirements — слой с зависимостями кэшируется отдельно
# от кода, пересборка после правки тестов идёт секунды, а не минуты.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# По умолчанию гоняем smoke — быстрая обратная связь. Конкретный набор
# переопределяется в docker-compose.yml или через `docker run ... pytest ...`.
CMD ["pytest", "-m", "smoke"]
