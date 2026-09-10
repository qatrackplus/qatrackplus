FROM nginx:alpine

# Remove default config
RUN rm -f /etc/nginx/nginx.conf /etc/nginx

# Copy custom configs
COPY nginx.conf /etc/nginx/
COPY configs/ /etc/nginx/configs/

# Copy snippets (locations file)
COPY snippets/ /etc/nginx/snippets/

# Copy container entrypoints (docker-entrypoint.d method supported by nginx image)
# see: https://github.com/nginx/docker-nginx/blob/master/entrypoint/docker-entrypoint.sh
# The entrypoint script is named 99-select-protocol.sh, which should run after the
# env var values are interpolated.
COPY docker-entrypoint.d/10-set-env-var-defaults.envsh /docker-entrypoint.d/10-set-env-var-defaults.envsh
COPY docker-entrypoint.d/15-select-protocol.sh /docker-entrypoint.d/15-select-protocol.sh

# Create volume mount points with matching UID/GID from Django
RUN chmod 755 /docker-entrypoint.d/15-select-protocol.sh \
    && mkdir -p /app/qatrack/media /app/qatrack/static \
    && chown -R 1000:1000 /app/qatrack/media /app/qatrack/static
