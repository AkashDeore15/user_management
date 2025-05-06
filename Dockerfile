# Define a base stage with a Debian Bookworm base image that includes the latest glibc update
FROM python:3.12-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=true \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    QR_CODE_DIR=/myapp/qr_codes \
    COVERAGE_FILE=/tmp/.coverage

WORKDIR /myapp

# Update system and install required packages without pinning the libc-bin version
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in /.venv
COPY requirements.txt .
RUN python -m venv /.venv \
    && . /.venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# Define a second stage for the runtime, using the same Debian Bookworm slim image
FROM python:3.12-slim-bookworm AS final

# Install required packages without pinning the libc-bin version
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the base stage
COPY --from=base /.venv /.venv

# Set environment variable to ensure all python commands run inside the virtual environment
ENV PATH="/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    QR_CODE_DIR=/myapp/qr_codes \
    COVERAGE_FILE=/tmp/.coverage

# Set the working directory
WORKDIR /myapp

# Create and switch to a non-root user
RUN useradd -m myuser

# Create the QR code directory
RUN mkdir -p ${QR_CODE_DIR} && \
    # Important: Make the entire /myapp directory writable by the myuser
    chown -R myuser:myuser /myapp && \
    # Ensure /tmp is writable (it should be by default, but just to be sure)
    chmod 1777 /tmp

# Copy application code with appropriate ownership
COPY --chown=myuser:myuser . .

# Switch to non-root user
USER myuser

# Inform Docker that the container listens on the specified port at runtime.
EXPOSE 8000

# Use ENTRYPOINT to specify the executable when the container starts.
ENTRYPOINT ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]