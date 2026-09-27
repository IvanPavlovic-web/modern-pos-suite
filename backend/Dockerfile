FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Kreiraj skriptu za cron
RUN mkdir -p /app/scripts && \
    if [ -f /app/scripts/backup.sh ]; then chmod +x /app/scripts/backup.sh; fi

# Cron job za backup u 3:00
RUN echo "0 3 * * * cd /app && /app/scripts/backup.sh >> /var/log/backup.log 2>&1" > /etc/cron.d/pos-backup && \
    chmod 0644 /etc/cron.d/pos-backup && \
    crontab /etc/cron.d/pos-backup

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]