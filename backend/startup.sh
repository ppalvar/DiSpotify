#!/bin/sh

ip route del default
ip route add default via 10.0.1.254

echo "Backend gateway set"

mkdir -p /app/data/db
mkdir -p /app/data/audios


python manage.py migrate
python manage.py runserver 0.0.0.0:8000