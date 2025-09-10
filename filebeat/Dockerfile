# filebeat/Dockerfile

# Start from the official Filebeat image
FROM docker.elastic.co/beats/filebeat:8.11.3

# Temporarily switch to the root user to modify file permissions
USER root

# Copy your custom filebeat.yml into the container
COPY filebeat.yml /usr/share/filebeat/filebeat.yml

# Fix the permissions of the config file as the root user
RUN chmod go-w /usr/share/filebeat/filebeat.yml

# Switch back to the default, non-root filebeat user for security
USER filebeat