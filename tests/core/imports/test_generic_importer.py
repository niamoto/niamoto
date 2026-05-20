"""Tests for the generic import engine."""

from niamoto.common.database import Database
from niamoto.core.imports.engine import GenericImporter
from niamoto.core.imports.registry import EntityKind, EntityRegistry


def test_duckdb_csv_import_generates_default_id_when_source_has_no_id(tmp_path):
    db = Database(str(tmp_path / "niamoto.duckdb"))
    try:
        registry = EntityRegistry(db)
        importer = GenericImporter(db, registry)
        csv_path = tmp_path / "occurrences.csv"
        csv_path.write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")

        result = importer.import_from_csv(
            entity_name="occurrences",
            table_name="dataset_occurrences",
            source_path=str(csv_path),
            kind=EntityKind.DATASET,
            id_field=None,
        )

        columns = db.get_table_columns("dataset_occurrences")
        entity = registry.get("occurrences")

        assert result.rows == 2
        assert columns[:3] == ["id", "name", "value"]
        assert entity.config["schema"]["id_field"] == "id"
        assert entity.config["schema"]["fields"][0]["name"] == "id"
    finally:
        db.close_db_session()
        db.engine.dispose()


def test_add_native_geometry_column_quotes_table_and_column_names(
    tmp_path, monkeypatch
):
    db = Database(str(tmp_path / "niamoto.duckdb"))
    executed_sql: list[str] = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def execute(self, statement):
            executed_sql.append(str(statement))

        def commit(self):
            return None

        def close(self):
            return None

    try:
        registry = EntityRegistry(db)
        importer = GenericImporter(db, registry)
        monkeypatch.setattr(db.engine, "connect", lambda: FakeConnection())

        importer._add_native_geometry_column(
            "dataset-occurrences", "geo pt", "geo pt_geom"
        )

        assert 'ALTER TABLE "dataset-occurrences"' in executed_sql[0]
        assert 'ADD COLUMN "geo pt_geom" GEOMETRY' in executed_sql[0]
        assert 'UPDATE "dataset-occurrences"' in executed_sql[1]
        assert 'ST_GeomFromText("geo pt")' in executed_sql[1]
    finally:
        db.close_db_session()
        db.engine.dispose()
