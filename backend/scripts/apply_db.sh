#!/usr/bin/env bash
# Apply schema and seed data to the database pointed at by DATABASE_URL.
# Safe to run repeatedly — schema uses IF NOT EXISTS, seed uses ON CONFLICT DO NOTHING.
#
# Usage:
#   DATABASE_URL=postgresql://user:pass@host:5432/dbname bash scripts/apply_db.sh

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Applying schema..."
psql "$DATABASE_URL" -f "$SCRIPT_DIR/../schema.sql"

echo "==> Seeding global_standards..."
psql "$DATABASE_URL" -f "$SCRIPT_DIR/seed_global_standards.sql"

echo "==> Done."
