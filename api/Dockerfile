FROM python:3.12.4-slim

COPY requirements.txt ./api/requirements.txt

RUN pip install --upgrade pip

RUN pip install -r ./api/requirements.txt

COPY . ./api

WORKDIR /api
