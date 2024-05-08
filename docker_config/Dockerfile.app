# codewithteddy web app Dockerfile

# Temp 'build' stage to install dependencies
FROM python:3.11-slim AS build
WORKDIR /app

# Set environment variables
# https://stackoverflow.com/questions/59732335/is-there-any-disadvantage-in-using-pythondontwritebytecode-in-docker
ENV PYTHONDONTWRITEBYTECODE 1
# https://stackoverflow.com/questions/59812009/what-is-the-use-of-pythonunbuffered-in-docker-file
ENV PYTHONUNBUFFERED 1

# Update package lists and install curl (to install 'uv')
# DL3008: Pin versions in apt get install
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    # Clean up to keep the docker image small
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Set virtual environment for 'uv'
ENV VIRTUAL_ENV=/opt/venv

# Install 'uv' then create a python virtual environment
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /root/.cargo/bin/uv venv /opt/venv


# Install python dependencies
COPY ./requirements-prod.txt .
# Install production dependencies with a cache for quicker future installs
RUN --mount=type=cache,target=/root/.cache \
    /root/.cargo/bin/uv pip install -r requirements-prod.txt

# Final production stage
FROM python:3.11-slim

# Update package lists and install curl (for healthcheck)
# DL3008: Pin versions in apt get install
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y curl --no-install-recommends && \
    # Clean up to keep the docker image small
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/venv /opt/venv

LABEL maintainer="Theodore Williams <theodore.f.williams@gmail.com>"


# Use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# Create the appropriate directories
ENV APP_HOME=/code
RUN mkdir "$APP_HOME"
WORKDIR $APP_HOME

# Create the app user
# This user should have same UID as user that cloned repo
RUN addgroup --system codewithteddy \
    && adduser --system --group codewithteddy \
    && usermod -u 1001 codewithteddy

# Copy all files into the APP_HOME directory
COPY app/ $APP_HOME/app

# chown all the files to the codewithteddy user
RUN chown -R codewithteddy:codewithteddy "$APP_HOME"

# Change to the app user
USER codewithteddy

EXPOSE 8000

# Using uvicorn as the server
CMD ["uvicorn", "app.web.main:create_app", "--factory", "--host=0.0.0.0", "--port=8000", "--proxy-headers"]

# Using gunicorn as the server
# CMD ["gunicorn",  "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind-address", "0.0.0.0:8000", "--access-logfile", "-", "--access-logformat", "%(h)s %(l)s %(u)s %(t)s '%(r)s' %(s)s %(b)s '%(f)s' '%(a)s'", "app.web.main:create_app()"]
