# Stage 1: Use an official Python runtime as a parent image
# We use the 'slim' version as it's smaller and more secure than the default.
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Install Poetry, Python's dependency manager.
# We use a specific version for reproducibility and run it as a separate layer for better caching.
RUN pip install poetry==2.1.4

# Copy only the files needed for dependency installation into the container.
# This is a crucial optimization. Docker caches this layer, and it will only be re-run
# if these specific files change, not every time you change your source code.
COPY poetry.lock pyproject.toml ./

# Install project dependencies using Poetry.
# --no-root: Prevents Poetry from trying to install the project package itself, which doesn't exist yet.
# --no-dev: Skips installing development dependencies like pytest, keeping the image smaller.
# --without-hashes: A workaround for some potential poetry/docker issues, can be removed if not needed.
RUN poetry install --no-root --only main

# Copy the rest of your application's source code into the container.
# This includes your 'app/' directory, 'webhook_server.py', etc.
COPY . .

# The command that will be run when the container starts.
# We will define the specific command to run (e.g., the web server or the worker)
# in our docker-compose.yml file, so we don't need a default CMD here.
# This makes the image more flexible.
