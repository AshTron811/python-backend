# Use Python 3.10-slim (includes distutils)
FROM python:3.10-slim

# Install minimal runtime deps and git for pip-git installs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
      git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install wheels + GitHub package
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# Copy your application code
COPY . .

EXPOSE 5000

# Run with Gunicorn in production
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
