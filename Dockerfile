FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for medical notes
RUN mkdir -p /app/notes /app/logs /app/feedback

COPY . .

# Make port 8000 available
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
