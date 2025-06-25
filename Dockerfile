# 1. Use Python 3.9-slim (distutils included)
FROM python:3.9-slim

# 2. Install minimal runtime deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Copy requirements and install only wheels
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# 4. Copy app code
COPY . .

# 5. Expose port and run
EXPOSE 5000
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
