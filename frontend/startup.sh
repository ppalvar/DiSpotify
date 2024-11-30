#!/bin/sh
sh /app/frontend.sh
node proxy.js &
npm install
npm run serve &
wait