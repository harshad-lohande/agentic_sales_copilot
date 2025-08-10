# Stage 1: The 'builder' stage
# This stage will install poetry and all project dependencies.
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Set Poetry specific environment variables
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true

WORKDIR /app

# Install Poetry
RUN pip install poetry==2.1.4

# Copy only the dependency definition files
COPY poetry.lock pyproject.toml ./

# Install dependencies into a local .venv directory
RUN poetry install --no-root --only main


# Stage 2: The final production stage
# This stage will be our final, lean image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy the virtual environment with all the dependencies from the 'builder' stage
COPY --from=builder /app/.venv ./.venv

# Copy the rest of your application's source code
COPY . .

# The command to run the application will be specified in docker-compose.yml,
# so no CMD is needed here, making the image more versatile.

# Create the entrypoint script directly inside the Dockerfile
RUN echo '#!/bin/sh' > /usr/local/bin/entrypoint.sh && \
    echo 'export PATH="/app/.venv/bin:$PATH"' >> /usr/local/bin/entrypoint.sh && \
    echo 'exec "$@"' >> /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

# Set the entrypoint for the container
ENTRYPOINT ["entrypoint.sh"]