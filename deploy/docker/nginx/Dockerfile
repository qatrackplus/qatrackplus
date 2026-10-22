FROM nginx:1.27-alpine

# Remove default config
RUN rm /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/
COPY qatrack-locations.conf /etc/nginx/snippets/

# The nginx image runs the scripts in /docker-entrypoint.d before it starts.
# This one writes the server configuration from deploy/docker/.env.
COPY 40-qatrack-config.sh /docker-entrypoint.d/
RUN chmod 755 /docker-entrypoint.d/40-qatrack-config.sh

# Create volume mount points with matching UID/GID from Django
RUN mkdir -p /usr/src/qatrackplus/qatrack/media /usr/src/qatrackplus/qatrack/static && \
    chown -R 1000:1000 /usr/src/qatrackplus/qatrack/media /usr/src/qatrackplus/qatrack/static
