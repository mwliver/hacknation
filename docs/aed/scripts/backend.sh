#!/bin/sh
# Helper for running backend commands in the repo's test image (Windows checkout with CRLF scripts).
# Uses --no-deps, so already running services (db, es, redis) are not recreated.
#   docs/aed/scripts/backend.sh test  <pytest args>   e.g. test -n1 mcod/aed/tests --no-cov
#   docs/aed/scripts/backend.sh run   <command>       e.g. run flake8 mcod/aed
set -e
cd "$(dirname "$0")/../../../backend_latest"
mode="$1"; shift
docker image inspect backend_latest-mcod-local-tests >/dev/null 2>&1 || docker tag mcod-app:local-tests backend_latest-mcod-local-tests
if [ "$mode" = "test" ]; then
  MSYS_NO_PATHCONV=1 docker compose -f docker-compose.local.yml run --rm --no-deps --entrypoint sh mcod-local-tests \
    -c 'tr -d "\r" < tests/tests-entrypoint.sh > /tmp/e.sh && sh /tmp/e.sh "$@"' -- "$@"
else
  MSYS_NO_PATHCONV=1 docker compose -f docker-compose.local.yml run --rm --no-deps --entrypoint "" mcod-local-tests "$@"
fi
