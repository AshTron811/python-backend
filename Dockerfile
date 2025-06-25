# Use a Debian-based Python image that includes distutils
FROM python:3.10-buster

# Install system dependencies needed at runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first for better layer caching
COPY requirements.txt .

# Upgrade pip/wheel/setuptools and install only binary wheels for heavy libs
RUN pip install --upgrade pip setuptools wheel && \
    pip install \
      --no-cache-dir \
      --only-binary=:all: \
      -r requirements.txt

# Now copy the rest of your app
COPY . .

EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
