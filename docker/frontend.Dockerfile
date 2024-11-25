FROM node:20-alpine

WORKDIR /app

COPY docker/frontend.sh .
RUN chmod +x ./frontend.sh