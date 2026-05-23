FROM python:3.12-slim

WORKDIR /Bot

COPY requirements/base.txt .
COPY .Moving\ /Bot
COPY ./database ./database

RUN pip install --no-cache-dir -r requirements/base.txt

CMD ["python3", "-m", "Moving.app"]
