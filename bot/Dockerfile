FROM python:3.11-slim

WORKDIR /app

# dependencies (requirements.txt נמצא בתוך /bot)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# code
COPY . /app

ENV PORT=8080

CMD ["python", "-u", "/app/bot.py"]
