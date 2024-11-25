FROM python:3.10-alpine

WORKDIR /app

COPY docker/backend.sh .
COPY requirements.txt .

RUN pip install -r requirements.txt
RUN chmod +x ./backend.sh

RUN apk add --no-cache ffmpeg