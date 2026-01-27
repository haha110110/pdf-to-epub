FROM python:3.9-slim

# Use host proxy
ENV http_proxy="http://127.0.0.1:10809"
ENV https_proxy="http://127.0.0.1:10809"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pandoc \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
