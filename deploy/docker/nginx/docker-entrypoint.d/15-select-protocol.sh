#!/bin/sh
#/docker-entrypoint.d/99-select-protocol.sh
set -eu

# This will select a default.conf.template based on the value of HTTP_OR_HTTPS,
# which should be either 'http' or 'https'.

# If https is selected, it will verify if the certificate files are readable.

certificate_file="${NGINX_SSL_CERTIFICATE_FILE:-}"
private_key_file="${NGINX_SSL_CERTIFICATE_KEY_FILE:-}"

if [ -z "$certificate_file" ]; then
    echo "NGINX_SSL_CERTIFICATE_FILE is required in HTTPS mode" >&2
    exit 1
fi

if [ -z "$private_key_file" ]; then
    echo "NGINX_SSL_CERTIFICATE_KEY_FILE is required in HTTPS mode" >&2
    exit 1
fi

protocol="${HTTP_OR_HTTPS:-http}"

case "$protocol" in
    http)
        source_file="/etc/nginx/configs/default.http.conf.template"
        ;;

    https)
        source_file="/etc/nginx/configs/default.https.conf.template"

        certificate="/etc/nginx/ssl/$certificate_file"
        private_key="/etc/nginx/ssl/$private_key_file"

        if [ ! -r "$certificate" ]; then
            echo "Missing or unreadable TLS certificate: $certificate" >&2
            exit 1
        fi

        if [ ! -r "$private_key" ]; then
            echo "Missing or unreadable TLS private key: $private_key" >&2
            exit 1
        fi
        ;;

    *)
        echo "HTTP_OR_HTTPS must be either 'http' or 'https'; got: $protocol" >&2
        exit 1
        ;;
esac

echo "Selecting nginx configuration for $protocol"
echo "Will copy $source_file to /etc/nginx/templates/default.conf.template"
cp "$source_file" /etc/nginx/templates/default.conf.template
