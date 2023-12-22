# Use a base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update \
    && apt-get install -y build-essential cmake gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Set CMake variables
ENV CMAKE_MAKE_PROGRAM=make
ENV CMAKE_C_COMPILER=gcc
ENV CMAKE_CXX_COMPILER=g++

# Copy the poetry files and install dependencies
COPY pyproject.toml poetry.lock .env .gitignore ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev

# Copy the application code
COPY src ./src

# Expose the FastAPI port
EXPOSE 8000

# Command to run the application
CMD ["poetry", "run", "python", "src/main.py"]

