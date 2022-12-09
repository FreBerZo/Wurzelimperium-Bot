# Dockerfile, Imager, Container
FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./wurzelbot /code/wurzelbot

ENV PYTHONPATH /code

CMD ["python", "-u", "wurzelbot/main.py"]
