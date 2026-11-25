#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/init.sh
scripts/migrate.sh

.venv/bin/python manage.py consume_payment_events &
consumer_pid=$!
.venv/bin/python manage.py runserver "$@" &
server_pid=$!

process_tree() {
    local pid
    for pid in "$@"; do
        process_tree $(pgrep -P "$pid" || true)
        echo "$pid"
    done
}

stop_all() {
    trap - EXIT INT TERM
    kill -TERM $(process_tree "$server_pid" "$consumer_pid") 2>/dev/null || true
    wait 2>/dev/null || true
}
trap stop_all EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

while kill -0 "$server_pid" 2>/dev/null && kill -0 "$consumer_pid" 2>/dev/null; do
    sleep 1
done
exit 1
