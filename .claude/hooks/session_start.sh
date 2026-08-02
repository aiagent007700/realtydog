#!/usr/bin/env bash
# RealtyDog — session sanity check. Surfaces problems, never blocks (always exit 0).
set +e
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RealtyDog — session sanity check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PY=python
command -v python3 >/dev/null 2>&1 && PY=python3

printf "  📦 Deps... "
if $PY -c "import fastapi, sqlalchemy, apscheduler, alembic" 2>/dev/null; then
  echo "✅"
else
  echo "⚠️  missing (run: pip install -r requirements.txt)"
fi

printf "  🧹 Ruff... "
if command -v ruff >/dev/null 2>&1; then
  n=$(ruff check . 2>/dev/null | grep -cE "^[^ ].*:[0-9]+:" )
  echo "⚠️  ${n:-0} finding(s) (non-blocking)"
else
  echo "skipped (ruff not installed)"
fi

printf "  🧪 Tests... "
if $PY -c "import pytest, fastapi" 2>/dev/null; then
  $PY -m pytest -q 2>&1 | tail -1
else
  if $PY -m py_compile app/*.py alembic/env.py alembic/versions/*.py 2>/dev/null; then
    echo "py_compile ✅ (pytest/deps not installed)"
  else
    echo "⚠️  syntax errors — check py_compile output"
  fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Read: README.md · STUBS.md · WIRING_STATUS.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
