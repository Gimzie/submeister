FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt requirements.txt

RUN apk add --no-cache alpine-sdk ffmpeg libffi-dev \
 && pip3 install -r requirements.txt \
 && apk del alpine-sdk

COPY . .

CMD ["python3", "/app/submeister.py"]
