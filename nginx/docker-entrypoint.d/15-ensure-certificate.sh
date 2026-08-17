#!/bin/sh
# Resolves the certbot/nginx bootstrap deadlock.
#
# The deadlock: the HTTPS server block needs ssl_certificate to point at a file
# that exists, or nginx refuses to start. On a fresh server that file doesn't
# exist yet. But certbot can only obtain it via an HTTP-01 challenge, which
# requires nginx to already be serving :80. Neither can go first.
#
# The fix: this script decides, at container start, which certificate the
# config should use, and writes that decision into an include file. If a real
# Let's Encrypt certificate exists it wins; otherwise a self-signed placeholder
# is generated so nginx can boot and serve the challenge that produces the real
# one.
#
# Deliberately NOT written into /etc/letsencrypt/live/<domain>/ — certbot treats
# that directory as its own, and finding foreign files there makes it issue into
# <domain>-0001 instead, silently breaking the path the config points at.

set -eu

DOMAIN="${DOMAIN:?DOMAIN must be set}"

LIVE_DIR="/etc/letsencrypt/live/${DOMAIN}"
PLACEHOLDER_DIR="/etc/nginx/placeholder-certs"
INCLUDE_FILE="/etc/nginx/ssl-certificate.conf"

mkdir -p /var/www/certbot

if [ -f "${LIVE_DIR}/fullchain.pem" ] && [ -f "${LIVE_DIR}/privkey.pem" ]; then
    echo "[ensure-certificate] using Let's Encrypt certificate for ${DOMAIN}"
    cat > "${INCLUDE_FILE}" <<EOF
ssl_certificate     ${LIVE_DIR}/fullchain.pem;
ssl_certificate_key ${LIVE_DIR}/privkey.pem;
EOF
else
    echo "[ensure-certificate] no certificate for ${DOMAIN} yet — generating placeholder"
    echo "[ensure-certificate] browsers WILL warn until certbot runs; see DEPLOY.md"

    mkdir -p "${PLACEHOLDER_DIR}"
    if [ ! -f "${PLACEHOLDER_DIR}/privkey.pem" ]; then
        openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
            -keyout "${PLACEHOLDER_DIR}/privkey.pem" \
            -out "${PLACEHOLDER_DIR}/fullchain.pem" \
            -subj "/CN=${DOMAIN}" 2>/dev/null
    fi

    cat > "${INCLUDE_FILE}" <<EOF
ssl_certificate     ${PLACEHOLDER_DIR}/fullchain.pem;
ssl_certificate_key ${PLACEHOLDER_DIR}/privkey.pem;
EOF
fi
