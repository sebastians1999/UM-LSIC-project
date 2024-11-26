# Use the official Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /tutoring_app

# Copy requirements and install dependencies
COPY requirements.txt /tutoring_app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY . /tutoring_app

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the app with Uvicorn
CMD ["uvicorn", "tutoring_app.main:app", "--host", "0.0.0.0", "--port", "8000"]