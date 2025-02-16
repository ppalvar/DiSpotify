#!/bin/sh

ip route del default
ip route add default via 10.0.1.254

echo "Backend gateway set"

python manage.py migrate
python manage.py runserver 0.0.0.0:8000