# Use the official Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /tutoring_app/app

# Copy requirements and install dependencies
COPY requirements.txt /tutoring_app/app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY /tutoring_app/app /tutoring_app/app

# Expose the port FastAPI runs on
EXPOSE 8080

# Non-secret environment variables
ENV LOCAL="false"
ENV GITLAB_REDIRECT_URI="https://fastapi-app-60415379904.europe-west1.run.app/auth/callback"

# Command to run the app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]