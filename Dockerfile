FROM python:3.7

RUN pip install fastapi uvicorn

EXPOSE 80

COPY ./dinky-vision dinky-vision

CMD ["uvicorn", "dinky-vision.main:app", "--reload", "--host", "0.0.0.0", "--port", "80"]