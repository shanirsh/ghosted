FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache gcc musl-dev python3-dev linux-headers

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CORS_ORIGINS=http://localhost:3000
ENV DOCKER_ENV=true

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
