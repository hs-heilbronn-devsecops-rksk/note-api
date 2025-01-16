# Use an official Python runtime as the base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy application files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 (required for Cloud Run)
EXPOSE 8080

# Start the application
CMD ["python", "main.py"]
