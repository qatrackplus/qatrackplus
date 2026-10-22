#!/bin/sh
# Writes the nginx server configuration for QATrack+ from the settings in
# deploy/docker/.env: ALLOWED_HOSTS, HTTP_OR_HTTPS and the NGINX_* settings.
set -eu
# ALLOWED_HOSTS may be '*': never expand it to file names.
set -f

conf=/etc/nginx/conf.d/qatrack.conf
locations=/etc/nginx/snippets/qatrack-locations.conf

fail() {
    echo "qatrack: $*" >&2
    exit 1
}

protocol="${HTTP_OR_HTTPS:-http}"
case "$protocol" in
    http|https) ;;
    *) fail "HTTP_OR_HTTPS must be http or https, not '$protocol'." ;;
esac
max_body="${NGINX_CLIENT_MAX_BODY_SIZE:-100m}"

# nginx passes on requests for the hosts QATrack+ accepts: NGINX_SERVER_NAME if
# set, otherwise ALLOWED_HOSTS (nginx reads Django's '.example.com' form the same
# way). Requests for any other host are dropped here. QATrack+ always accepts
# localhost and 127.0.0.1, which the health checks use. With '*', nginx passes
# on every host and QATrack+ checks it.
hosts="${NGINX_SERVER_NAME:-$(printf '%s' "${ALLOWED_HOSTS:-}" | tr ',' ' ')}"
names=""
catch_all=false
for host in $hosts localhost 127.0.0.1; do
    case " $names " in
        *" $host "*) ;;
        *) names="${names:+$names }$host" ;;
    esac
    [ "$host" = "*" ] && catch_all=true
done
if [ "$catch_all" = true ]; then
    names="_"
    default=" default_server"
else
    default=""
fi

if [ "$protocol" = https ]; then
    cert="/etc/nginx/ssl/${NGINX_SSL_CERTIFICATE:-cert.pem}"
    key="/etc/nginx/ssl/${NGINX_SSL_CERTIFICATE_KEY:-key.pem}"
    [ -r "$cert" ] || fail "HTTP_OR_HTTPS=https, but there is no certificate at $cert (deploy/docker/user-data/ssl on the host)."
    [ -r "$key" ] || fail "HTTP_OR_HTTPS=https, but there is no private key at $key (deploy/docker/user-data/ssl on the host)."
fi

{
    if [ "$catch_all" = false ]; then
        cat <<CONF
# Requests for hosts QATrack+ does not serve are closed without an answer.
server {
    listen 80 default_server;
    server_name _;
    return 444;
}

CONF
        if [ "$protocol" = https ]; then
            cat <<CONF
server {
    listen 443 ssl default_server;
    server_name _;
    ssl_reject_handshake on;
}

CONF
        fi
    fi

    if [ "$protocol" = http ]; then
        cat <<CONF
server {
    listen 80$default;
    server_name $names;
    client_max_body_size $max_body;
    charset utf-8;

    include $locations;
}
CONF
    else
        cat <<CONF
server {
    listen 80$default;
    server_name $names;

    location = /nginx-health {
        access_log off;
        default_type text/plain;
        return 200 "OK\n";
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl$default;
    server_name $names;
    client_max_body_size $max_body;
    charset utf-8;

    ssl_certificate $cert;
    ssl_certificate_key $key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    include $locations;
}
CONF
    fi
} > "$conf"

echo "qatrack: $protocol, serving: $names"
