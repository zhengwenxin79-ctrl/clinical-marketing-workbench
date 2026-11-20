-- 只新增维护日志；业务原表和既有分析版本不重建。
CREATE TABLE IF NOT EXISTS maintenance_runs (
 run_id TEXT PRIMARY KEY,
 source_sha256 TEXT NOT NULL,
 baseline_sha256 TEXT NOT NULL,
 diff_sha256 TEXT NOT NULL,
 run_directory TEXT NOT NULL,
 confirmed_at TEXT NOT NULL,
 confirmed_by TEXT NOT NULL,
 changed_fields INTEGER NOT NULL,
 source_material_id TEXT,
 status TEXT NOT NULL CHECK(status IN ('confirmed_no_change','confirmed_updated'))
);
CREATE TABLE IF NOT EXISTS maintenance_changes (
 run_id TEXT NOT NULL REFERENCES maintenance_runs(run_id),
 ordinal INTEGER NOT NULL,
 entity TEXT NOT NULL,
 entity_id TEXT NOT NULL,
 field TEXT NOT NULL,
 before_json TEXT NOT NULL,
 after_json TEXT NOT NULL,
 source_locator TEXT NOT NULL,
 PRIMARY KEY(run_id,ordinal)
);
CREATE TABLE IF NOT EXISTS maintenance_events (
 event_id TEXT PRIMARY KEY,
 run_id TEXT NOT NULL REFERENCES maintenance_runs(run_id),
 occurred_at TEXT NOT NULL,
 event_kind TEXT NOT NULL,
 detail_json TEXT NOT NULL
);
