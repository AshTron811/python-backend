# Use an official Python 3.10 image (buster variant includes distutils by default)
FROM python:3.10-buster

# Install system dependencies required for building dlib, OpenCV, etc.
RUN apt-get update && \
    apt-get install -y \
      cmake \
      build-essential \
      libopenblas-dev \
      liblapack-dev \
      libgl1-mesa-glx \
      python3-distutils && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the port your Flask app runs on
EXPOSE 5000

# Set the default command to run your Python backend
CMD ["python", "main.py"]
