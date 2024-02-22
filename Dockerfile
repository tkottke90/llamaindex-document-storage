FROM python:3.11

WORKDIR /usr/app

COPY ./requirements.txt .

RUN pip3 install -r requirements.txt
