FROM nginx:1.27-alpine

# Remove default config
RUN rm /etc/nginx/nginx.conf
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configs
COPY nginx.conf /etc/nginx/
COPY conf.d/ /etc/nginx/conf.d/

# Create volume mount points with matching UID/GID from Django
RUN mkdir -p /usr/src/qatrackplus/qatrack/media /usr/src/qatrackplus/qatrack/static && \
    chown -R 1000:1000 /usr/src/qatrackplus/qatrack/media /usr/src/qatrackplus/qatrack/static

