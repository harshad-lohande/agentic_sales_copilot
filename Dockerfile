# Stage 1: The 'builder' stage
# This stage will install poetry and all project dependencies.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Tell Poetry not to create a virtual environment, but install directly to system site-packages
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Install Poetry
RUN pip install poetry==2.1.4

# Copy only the dependency definition files
COPY poetry.lock pyproject.toml ./

# Install dependencies directly into the system path
RUN poetry install --no-root --only main


# Stage 2: The final production stage
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from the builder stage to the final image's system path
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application source code
COPY . .

# Change ownership of the app directory to the new user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# No entrypoint is needed because the executables are now in the global PATH