#!/bin/sh
# Start as root only long enough to give the app user the state volume, which
# hosts such as Fly.io mount owned by root, then run the server as that user.
set -eu
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/state
    chown -R appuser:appuser /app/state
    # setpriv keeps HOME=/root; libpq then fails probing /root/.postgresql for a
    # client certificate it cannot read, so point HOME at the app user's home.
    export HOME=/home/appuser
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi
exec "$@"
