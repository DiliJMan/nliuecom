from django.db import migrations

TABLE = "audit_auditevent"

SQLITE_UP = [
    f"""CREATE TRIGGER IF NOT EXISTS {TABLE}_no_update BEFORE UPDATE ON {TABLE}
        BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END""",
    f"""CREATE TRIGGER IF NOT EXISTS {TABLE}_no_delete BEFORE DELETE ON {TABLE}
        BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END""",
]
SQLITE_DOWN = [
    f"DROP TRIGGER IF EXISTS {TABLE}_no_update",
    f"DROP TRIGGER IF EXISTS {TABLE}_no_delete",
]

POSTGRES_UP = [
    """CREATE OR REPLACE FUNCTION audit_events_immutable() RETURNS trigger AS $$
       BEGIN RAISE EXCEPTION 'audit events are immutable'; END; $$ LANGUAGE plpgsql""",
    f"""CREATE TRIGGER {TABLE}_immutable BEFORE UPDATE OR DELETE ON {TABLE}
        FOR EACH ROW EXECUTE FUNCTION audit_events_immutable()""",
]
POSTGRES_DOWN = [f"DROP TRIGGER IF EXISTS {TABLE}_immutable ON {TABLE}"]


def _run(statements_by_vendor):
    def apply(apps, schema_editor):
        for statement in statements_by_vendor.get(schema_editor.connection.vendor, []):
            schema_editor.execute(statement)

    return apply


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [
        migrations.RunPython(
            _run({"sqlite": SQLITE_UP, "postgresql": POSTGRES_UP}),
            _run({"sqlite": SQLITE_DOWN, "postgresql": POSTGRES_DOWN}),
        )
    ]
