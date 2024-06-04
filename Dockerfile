FROM python:3.10

WORKDIR /app

RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY Makefile .
COPY config.json .
COPY src/ src/

RUN make virtualenv_run

CMD ["make", "run"]
