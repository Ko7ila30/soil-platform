# Dockerfile -- Flask application container
#
# Uses the official Python 3.15 slim image (Debian-based, small footprint).
# The app runs on port 5000 inside the container, mapped to 5000 on the host.

FROM python:3.15-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first so Docker can cache the pip install layer.
# This layer is only rebuilt when requirements.txt changes.
COPY requirements.txt .

# Install Python dependencies.
# --no-cache-dir keeps the image smaller.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Flask will listen on all interfaces inside the container (0.0.0.0)
# so Docker can forward traffic to it from the host.
# Debug mode is OFF when running in Docker -- use the host venv for development.
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "app.py"]
