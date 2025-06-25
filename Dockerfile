# Use Python 3.11-slim (distutils included)
FROM python:3.11-slim

# Install minimal runtime deps plus git for pip-git installs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
      git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy your requirements file (we won't use it directly for face-recognition)
COPY requirements.txt .

# Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# 1) Install the binary dlib package
RUN pip install --no-cache-dir --only-binary=:all: dlib-bin==19.24.6

# 2) Install face_recognition_models from GitHub
RUN pip install --no-cache-dir \
    git+https://github.com/ageitgey/face_recognition_models.git@master#egg=face_recognition_models

# 3) Install the rest of your deps from requirements.txt, excluding dlib
RUN pip install --no-cache-dir --only-binary=:all: \
    -r <(grep -vE "^(dlib|face-recognition)" requirements.txt)

# 4) Finally install face-recognition itself without dependencies
RUN pip install --no-cache-dir --no-deps face-recognition==1.3.0

# Copy application code
COPY . .

EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
