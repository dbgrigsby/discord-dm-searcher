FROM python:3.9-buster AS base

WORKDIR /app

RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .

RUN python3 -m venv virtualenv_run && \
    virtualenv_run/bin/pip install --upgrade pip && \
    virtualenv_run/bin/pip install --prefer-binary -r requirements.txt

COPY Makefile .
COPY config.json .
COPY entrypoint.sh .
COPY src/ src/

RUN . virtualenv_run/bin/activate

ENTRYPOINT ["./entrypoint.sh"]

CMD ["make", "run"]