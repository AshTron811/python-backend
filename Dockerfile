# 1) Use Python 3.11-slim (includes distutils)
FROM python:3.11-slim

# 2) Install minimal runtime deps + git for pip-git installs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
      git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3) Copy requirements file
COPY requirements.txt .

# 4) Upgrade pip/setuptools/wheel
RUN pip install --upgrade pip setuptools wheel

# 5) Install binary dlib
RUN pip install --no-cache-dir --only-binary=:all: dlib-bin==19.24.6

# 6) Install face_recognition_models from GitHub
RUN pip install --no-cache-dir \
    git+https://github.com/ageitgey/face_recognition_models.git@master#egg=face_recognition_models

# 7) Install all other deps (excluding dlib and face-recognition) via a temp file
RUN grep -v -E '^(dlib|face-recognition)' requirements.txt > temp-reqs.txt && \
    pip install --no-cache-dir --only-binary=:all: -r temp-reqs.txt && \
    rm temp-reqs.txt

# 8) Install face-recognition itself without pulling its own dlib dependency
RUN pip install --no-cache-dir --no-deps face-recognition==1.3.0

# 9) Copy app code
COPY . .

# 10) Expose port and run
EXPOSE 5000
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
