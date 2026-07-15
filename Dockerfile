FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python packages directly (isolated inside the container, venv not required)
RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    psycopg2-binary

# Copy project files
COPY app.py sync.py daemon.py entrypoint.sh /app/

# Expose port
EXPOSE 8080

# Run entrypoint script
CMD ["/app/entrypoint.sh"]
