#!/bin/sh
sh /app/frontend.sh
node proxy.js &
npm run serve &
wait