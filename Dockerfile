# Use an official Python runtime as the base image
FROM python:3.9-slim

# Install Ghostscript and other system dependencies
RUN apt-get update && apt-get install -y ghostscript && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Collect static files (if needed)
RUN python manage.py collectstatic --noinput

# Expose the port your Django app will run on
EXPOSE 8000

# Command to run your Django application
CMD ["gunicorn", "my_render.wsgi:application", "--bind", "0.0.0.0:8000"]