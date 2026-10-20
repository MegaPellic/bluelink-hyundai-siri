FROM python:3.12-slim

WORKDIR /app

RUN pip install flask "hyundai-kia-connect-api>=4.38.0"

COPY app.py .

CMD ["python", "app.py"]
