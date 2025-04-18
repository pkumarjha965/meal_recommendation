# Use an official lightweight Python image
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .
WORKDIR /app/airflow
# ENTRYPOINT ["cd", "airflow"]
# Command to run the app
CMD ["uvicorn", "meal_suggest_flow:app", "--host", "0.0.0.0", "--port", "8000"]
