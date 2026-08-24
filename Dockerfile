FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt groq

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Set environment variables default
ENV HOST=0.0.0.0

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
