#!/bin/sh
# Lint AED backend code with the same tools/versions as .pre-commit-config.yaml (black is not in the image).
# Pass --fix to apply black/isort.
dir="$(dirname "$0")"
if [ "$1" = "--fix" ]; then BLACK=""; ISORT=""; else BLACK="--check"; ISORT="--check-only --diff"; fi
sh "$dir/backend.sh" run sh -c "pip install -q black==24.3.0 isort==5.12.0 >/dev/null 2>&1; \
  isort $ISORT --multi-line 3 --trailing-comma --line-length 100 --combine-as --profile black mcod/aed \
  && black $BLACK --line-length 130 mcod/aed && flake8 --max-line-length 130 mcod/aed && echo LINT_OK"
