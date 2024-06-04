FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY Makefile .
COPY config.json .
COPY src/ src/

CMD ["make", "run"]
