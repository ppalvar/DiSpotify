#!/bin/sh

ip route del default
ip route add default via 10.0.2.254

echo "Frontend gateway set"

node proxy.js &
# npm install
npm run serve &
wait