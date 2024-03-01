FROM python:3.11

WORKDIR /usr/app

COPY ./requirements.txt .

RUN pip3 install -r requirements.txt

EXPOSE 8080
CMD [ "python3.11", "main.py" ]
