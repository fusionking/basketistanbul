# Use an official Python runtime as a parent image
FROM python:3.10

# Adding backend directory to make absolute filepaths consistent across services
WORKDIR /app/backend

# Install Python dependencies
COPY ./requirements /app/backend/requirements
RUN pip install -r requirements/development.txt

# Add the rest of the code
COPY . /app/backend

# Make port 8000 available for the app
EXPOSE 8000

# Be sure to use 0.0.0.0 for the host within the Docker container,
# otherwise the browser won't be able to find it
RUN chmod +x /app/backend/docker/server-entrypoint.sh
RUN chmod +x /app/backend/docker/worker-entrypoint.sh
