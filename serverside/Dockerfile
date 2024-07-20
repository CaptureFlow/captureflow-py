# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install any needed packages specified in requirements.txt
COPY ./requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir -r requirements.txt

# Install docker to start client's docker images.
RUN apt-get update -y && apt-get install git curl -y
RUN curl -fsSL https://get.docker.com -o get-docker.sh
RUN sh get-docker.sh

# Copy the current directory contents into the container at /usr/src/app
COPY . .

ENV CAPTUREFLOW_DEV_SERVER=true

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run server.py when the container launches
CMD ["opentelemetry-instrument", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["tail", "-f", "/dev/null"]
