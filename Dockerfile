# 1) Switch to Python 3.11 (slim variant has distutils)
FROM python:3.11-slim

# 2) Install minimal runtime deps and git for pip-git installs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
      git \
    && rm -rf /var/lib/apt/lists/*

# 3) Set working directory
WORKDIR /app

# 4) Copy requirements and install 
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# 5) Copy application code
COPY . .

# 6) Expose port
EXPOSE 5000

# 7) Production server
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
