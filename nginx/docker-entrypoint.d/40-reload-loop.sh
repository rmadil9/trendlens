#!/bin/sh
# Periodically reloads nginx so renewed certificates are picked up.
#
# certbot writes a renewed certificate as new files on disk, but nginx only
# reads certificates at startup or on reload. Without this the site keeps
# serving the expired certificate — a failure that surfaces ~90 days after
# deploy, long after anyone is watching for it.
#
# This lives here rather than in the compose `command:` for a specific reason.
# The nginx image's entrypoint runs these scripts only when its first argument
# is exactly "nginx":
#
#     if [ "$1" = "nginx" -o "$1" = "nginx-debug" ]; then ...run /docker-entrypoint.d/... fi
#
# Overriding `command:` with a shell wrapper makes $1 "/bin/sh", so the whole
# init chain — envsubst templating included — is skipped silently. No error, no
# warning; the container just starts with an unrendered config. Keeping the
# command as plain `nginx` and backgrounding the loop from here preserves the
# init chain.
#
# The subshell is orphaned when the entrypoint execs nginx, which is fine: it
# keeps running, and the container's lifetime is tied to nginx as PID 1.

set -eu

(
    while :; do
        sleep 6h
        nginx -s reload 2>/dev/null || true
    done
) &

echo "[reload-loop] certificate reload scheduled every 6h"
