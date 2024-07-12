FROM python:3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    lsb-release \
    unixodbc-dev \
    freetds-common \
    freetds-dev \
    tdsodbc \
    vim \
    make \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to /code
WORKDIR /code

# Copy the Python requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint scripts
COPY entrypoint.sh celery_entrypoint.sh ./




