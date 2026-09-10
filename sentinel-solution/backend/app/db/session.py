from __future__ import annotations

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from .. import config
from .models import Base

logger = logging.getLogger("sentinel.db")

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Columns added after the initial schema shipped. `create_all` only creates
# MISSING TABLES — it never alters an existing one — so an already-created DB
# would be missing these and queries referencing them would fail with
# "no such column". This project has no migration framework (Alembic), so
# this is a minimal, idempotent, additive migration: add the column only if
# it isn't already present. Additive-only by design — it never drops or
# rewrites data. (table, column, SQL column definition)
_ADDITIVE_MIGRATIONS = [
    ("alert", "status", "VARCHAR DEFAULT 'new' NOT NULL"),
    ("alert", "status_updated_by", "VARCHAR"),
    ("alert", "status_updated_at", "DATETIME"),
    ("vehicle_event", "crop_path", "VARCHAR"),
    ("vehicle_event", "bbox_x1", "FLOAT"),
    ("vehicle_event", "bbox_y1", "FLOAT"),
    ("vehicle_event", "bbox_x2", "FLOAT"),
    ("vehicle_event", "bbox_y2", "FLOAT"),
    ("vehicle_identity", "last_camera_id", "VARCHAR"),
    ("camera_registry", "camera_type", "VARCHAR"),
    ("camera_registry", "is_restricted_zone", "BOOLEAN DEFAULT 0 NOT NULL"),
    ("camera_registry", "expected_direction_deg", "FLOAT"),
    ("alert", "alert_type", "VARCHAR DEFAULT 'watchlist' NOT NULL"),
    ("camera_registry", "install_date", "DATETIME"),
    ("camera_registry", "coverage_radius_m", "FLOAT"),
]


def _apply_additive_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, column, coldef in _ADDITIVE_MIGRATIONS:
            if table not in existing_tables:
                continue  # create_all will build it fresh, with all columns
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column in cols:
                continue
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {coldef}'))
            logger.info("migrated: added %s.%s", table, column)


def _ensure_vehicle_identity_plate_unique(existing_tables: set) -> None:
    """`vehicle_identity.plate` gained a UNIQUE constraint after this project
    already had DBs in the wild with duplicate-plate identity rows (the
    check-then-insert race in identity.py, now fixed there too — see its
    IntegrityError handling, which depends on this constraint existing).
    `create_all` only builds the constraint for brand-new tables, so an
    already-existing `vehicle_identity` table needs its duplicates merged
    before the unique index can be created, or the index creation itself
    would fail against corrupted data.
    """
    if "vehicle_identity" not in existing_tables:
        return  # fresh table from create_all already has the constraint
    inspector = inspect(engine)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("vehicle_identity")}
    if "ix_vehicle_identity_plate_unique" in existing_indexes:
        return
    with engine.begin() as conn:
        dupes = conn.execute(text(
            "SELECT plate, MIN(id) FROM vehicle_identity "
            "WHERE plate IS NOT NULL GROUP BY plate HAVING COUNT(*) > 1"
        )).fetchall()
        for plate, keep_id in dupes:
            dup_ids = [row[0] for row in conn.execute(
                text("SELECT id FROM vehicle_identity WHERE plate = :plate AND id != :keep_id"),
                {"plate": plate, "keep_id": keep_id},
            ).fetchall()]
            if not dup_ids:
                continue
            placeholders = ", ".join(str(i) for i in dup_ids)  # ids only, not user input
            conn.execute(text(
                f"UPDATE vehicle_event SET identity_id = :keep_id WHERE identity_id IN ({placeholders})"
            ), {"keep_id": keep_id})
            conn.execute(text(f"DELETE FROM vehicle_identity WHERE id IN ({placeholders})"))
            logger.warning(
                "merged %d duplicate vehicle_identity row(s) for plate %s into id=%s "
                "(pre-existing DB corrupted by the identity-resolution race, now fixed)",
                len(dup_ids), plate, keep_id,
            )
        conn.execute(text(
            "CREATE UNIQUE INDEX ix_vehicle_identity_plate_unique "
            "ON vehicle_identity(plate) WHERE plate IS NOT NULL"
        ))


def _check_models_match_db() -> None:
    """Every new model column needs a matching entry in
    `_ADDITIVE_MIGRATIONS`, and nothing enforced that until now — a missed
    entry only surfaced as a runtime "no such column" error against an
    already-existing DB, potentially long after the column was added.
    Found by software-engineering review 2026-09-04. Runs AFTER migrations
    are applied, so this only fires on a genuine miss, not a column this
    same startup just added. Loud (raises) rather than silent, since the
    alternative is exactly the silent-landmine failure mode being fixed."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    missing = []
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue  # create_all just built this table fresh, in full
        db_columns = {c["name"] for c in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in db_columns:
                missing.append(f"{table_name}.{column.name}")
    if missing:
        raise RuntimeError(
            "Model/DB schema mismatch after migrations ran — these columns "
            f"exist on the model but not in the database: {', '.join(missing)}. "
            "Add a matching entry to _ADDITIVE_MIGRATIONS in db/session.py."
        )


def init_db() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    Base.metadata.create_all(engine)
    _apply_additive_migrations()
    _ensure_vehicle_identity_plate_unique(existing_tables)
    _check_models_match_db()
