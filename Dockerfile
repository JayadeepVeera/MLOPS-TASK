FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY run.py config.yaml ./
COPY data.csv .

# Create output directories
RUN mkdir -p logs metrics

# Run the pipeline
CMD ["python", "run.py", "--input", "data.csv", "--config", "config.yaml", "--output", "metrics/metrics.json", "--log-file", "logs/run.log"]
