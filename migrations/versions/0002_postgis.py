"""PostGIS geography columns, sync triggers and spatial indexes (PostgreSQL only).

Adds `geog geography(Point,4326)` to spatial tables, kept in sync with lat/lng by a trigger
(so ORM code stays dialect-neutral), plus GIST indexes used by ST_DWithin in
services/spatial.py. On SQLite (dev/test) this migration is a no-op and the app falls back
to bbox + haversine.

Revision ID: 0002_postgis
Revises: 0001_baseline
"""
from alembic import op

revision = "0002_postgis"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

TABLES = {
    "disease_reports": ("lat", "lng"),
    "veterinary_cases": ("lat", "lng"),
    "veterinarian_profiles": ("current_lat", "current_lng"),
    "surveillance_observations": ("lat", "lng"),
    "veterinary_facilities": ("lat", "lng"),
    "laboratories": ("lat", "lng"),
    "herds": ("lat", "lng"),
}


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    for table, (lat, lng) in TABLES.items():
        fn = f"{table}_geog_sync"
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS geog geography(Point, 4326)")
        op.execute(f"""
            CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger AS $$
            BEGIN
              IF NEW.{lat} IS NULL OR NEW.{lng} IS NULL OR (NEW.{lat} = 0 AND NEW.{lng} = 0) THEN
                NEW.geog := NULL;
              ELSE
                NEW.geog := ST_SetSRID(ST_MakePoint(NEW.{lng}, NEW.{lat}), 4326)::geography;
              END IF;
              RETURN NEW;
            END $$ LANGUAGE plpgsql""")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{fn} ON {table}")
        op.execute(f"CREATE TRIGGER trg_{fn} BEFORE INSERT OR UPDATE OF {lat}, {lng} ON {table} FOR EACH ROW EXECUTE FUNCTION {fn}()")
        op.execute(f"UPDATE {table} SET geog = ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326)::geography WHERE {lat} IS NOT NULL AND {lng} IS NOT NULL AND NOT ({lat} = 0 AND {lng} = 0)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_geog ON {table} USING GIST (geog)")
    # Composite indexes for common dashboard filters
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_district_created ON disease_reports (district, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cases_vet_status ON veterinary_cases (assigned_vet_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_claim ON jobs (status, run_after)")
    # Audit log is append-only at the database level too.
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END $$ LANGUAGE plpgsql""")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_immutable ON audit_logs")
    op.execute("CREATE TRIGGER trg_audit_immutable BEFORE UPDATE OR DELETE ON audit_logs FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS trg_audit_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable()")
    for table in TABLES:
        fn = f"{table}_geog_sync"
        op.execute(f"DROP TRIGGER IF EXISTS trg_{fn} ON {table}")
        op.execute(f"DROP FUNCTION IF EXISTS {fn}()")
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_geog")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS geog")
