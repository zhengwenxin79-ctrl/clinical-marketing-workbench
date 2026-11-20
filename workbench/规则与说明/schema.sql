PRAGMA foreign_keys=ON;
PRAGMA user_version=1;
CREATE TABLE import_batches (
 import_id TEXT PRIMARY KEY NOT NULL, fingerprint TEXT NOT NULL UNIQUE, imported_on TEXT NOT NULL,
 imported_at TEXT NOT NULL, source_observed_on TEXT NOT NULL, source_manifest TEXT NOT NULL,
 importer_version TEXT NOT NULL, new_collection INTEGER NOT NULL CHECK(new_collection=0), notes TEXT NOT NULL
);
CREATE TABLE source_materials (
 material_id TEXT PRIMARY KEY NOT NULL, import_id TEXT NOT NULL REFERENCES import_batches,
 relative_path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL,
 material_kind TEXT NOT NULL, source_url TEXT, reading_level TEXT NOT NULL,
 source_observed_on TEXT, original_path TEXT NOT NULL, original_sha256 TEXT NOT NULL,
 is_derived INTEGER NOT NULL CHECK(is_derived IN(0,1))
);
CREATE TABLE conference_series (
 series_id TEXT PRIMARY KEY NOT NULL, abbreviation TEXT NOT NULL, name_original TEXT NOT NULL,
 evidence_material_id TEXT NOT NULL REFERENCES source_materials
);
CREATE TABLE conference_editions (
 conference_id TEXT PRIMARY KEY NOT NULL, series_id TEXT NOT NULL REFERENCES conference_series,
 year INTEGER NOT NULL, edition_label TEXT, name_original TEXT NOT NULL, organizer TEXT,
 region TEXT, country TEXT, city TEXT, format TEXT, start_date TEXT, end_date TEXT,
 local_timezone TEXT, timezone_basis TEXT, official_url TEXT, metadata_status TEXT NOT NULL,
 metadata_material_id TEXT NOT NULL REFERENCES source_materials, source_locator TEXT NOT NULL,
 metadata_gaps TEXT NOT NULL, UNIQUE(series_id,year)
);
CREATE TABLE sessions (
 session_id TEXT PRIMARY KEY NOT NULL, conference_id TEXT NOT NULL REFERENCES conference_editions,
 source_session_id TEXT NOT NULL, title_original TEXT NOT NULL, date_original TEXT,
 local_date TEXT, room_original TEXT, material_id TEXT NOT NULL REFERENCES source_materials,
 source_locator TEXT NOT NULL, UNIQUE(conference_id,source_session_id)
);
CREATE TABLE agenda_items (
 agenda_item_id TEXT PRIMARY KEY NOT NULL, conference_id TEXT NOT NULL REFERENCES conference_editions,
 session_id TEXT NOT NULL REFERENCES sessions, source_code TEXT, source_order INTEGER NOT NULL,
 title_original TEXT NOT NULL, format_original TEXT NOT NULL, date_original TEXT,
 local_date TEXT, time_original TEXT, start_time TEXT, end_time TEXT, room_original TEXT,
 source_url TEXT, evidence_level TEXT NOT NULL CHECK(evidence_level='planned_agenda'),
 material_id TEXT NOT NULL REFERENCES source_materials, source_locator TEXT NOT NULL,
 raw_json TEXT NOT NULL CHECK(json_valid(raw_json)), UNIQUE(conference_id,source_order)
);
CREATE UNIQUE INDEX agenda_source_code ON agenda_items(conference_id,source_code) WHERE source_code IS NOT NULL;
CREATE TABLE reports (
 report_id TEXT PRIMARY KEY NOT NULL, agenda_item_id TEXT NOT NULL UNIQUE REFERENCES agenda_items,
 conference_id TEXT NOT NULL REFERENCES conference_editions, source_report_code TEXT NOT NULL,
 legacy_report_id TEXT NOT NULL, legacy_evidence_id TEXT NOT NULL UNIQUE,
 report_format TEXT NOT NULL CHECK(report_format IN('大会报告','专题报告','论文发言')),
 evidence_status TEXT NOT NULL CHECK(evidence_status IN('agenda_only','abstract_results','presentation_results','paper_linked')),
 has_results INTEGER NOT NULL CHECK(has_results IN(0,1)), result_text TEXT,
 independent_study_status TEXT NOT NULL CHECK(independent_study_status IN('not_established','pending','linked_no_independence_claim')),
 UNIQUE(conference_id,source_report_code)
);
CREATE TABLE people (
 person_id TEXT PRIMARY KEY NOT NULL, source_identity_key TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
 institution_source TEXT NOT NULL, identity_status TEXT NOT NULL,
 legacy_person_id TEXT UNIQUE, mapping_material_id TEXT NOT NULL REFERENCES source_materials,
 identity_note TEXT NOT NULL
);
CREATE TABLE agenda_participants (
 agenda_item_id TEXT NOT NULL REFERENCES agenda_items, ordinal INTEGER NOT NULL,
 person_id TEXT NOT NULL REFERENCES people, agenda_role TEXT NOT NULL,
 name_original TEXT NOT NULL, institution_original TEXT NOT NULL, profile_url TEXT,
 role_basis TEXT NOT NULL, PRIMARY KEY(agenda_item_id,ordinal)
);
CREATE TABLE session_chairs (
 session_id TEXT NOT NULL REFERENCES sessions, ordinal INTEGER NOT NULL,
 person_id TEXT NOT NULL REFERENCES people, name_original TEXT NOT NULL,
 institution_original TEXT NOT NULL, profile_url TEXT, PRIMARY KEY(session_id,ordinal)
);
CREATE TABLE person_profiles (
 profile_id TEXT PRIMARY KEY NOT NULL, person_id TEXT NOT NULL REFERENCES people,
 import_id TEXT NOT NULL REFERENCES import_batches, profile_url TEXT NOT NULL,
 read_status TEXT NOT NULL, has_substantive_bio INTEGER NOT NULL CHECK(has_substantive_bio IN(0,1)),
 extracted_text TEXT, fetch_error TEXT, raw_material_id TEXT REFERENCES source_materials,
 evidence_material_id TEXT NOT NULL REFERENCES source_materials, source_locator TEXT NOT NULL,
 source_observed_on TEXT, UNIQUE(person_id,import_id,profile_url)
);
CREATE TABLE academic_role_claims (
 claim_id TEXT PRIMARY KEY NOT NULL, person_id TEXT NOT NULL REFERENCES people,
 profile_id TEXT REFERENCES person_profiles, role_phrase TEXT NOT NULL, role_level TEXT NOT NULL,
 tenure_status TEXT NOT NULL CHECK(tenure_status IN('historical_mentioned','not_independently_verified')),
 source_material_id TEXT NOT NULL REFERENCES source_materials, source_locator TEXT NOT NULL,
 source_note TEXT NOT NULL, verification_status TEXT NOT NULL CHECK(verification_status='conference_bio_claim')
);
CREATE TABLE analysis_versions (
 analysis_version_id TEXT PRIMARY KEY NOT NULL, conference_id TEXT NOT NULL REFERENCES conference_editions,
 analysis_kind TEXT NOT NULL, rule_label TEXT NOT NULL, review_status TEXT NOT NULL,
 is_current_snapshot INTEGER NOT NULL CHECK(is_current_snapshot IN(0,1)),
 scoring_enabled INTEGER NOT NULL CHECK(scoring_enabled=0),
 material_id TEXT NOT NULL REFERENCES source_materials, method_note TEXT NOT NULL
);
CREATE UNIQUE INDEX active_analysis_snapshot ON analysis_versions(conference_id,analysis_kind) WHERE is_current_snapshot=1;
CREATE TABLE research_topics (
 topic_id TEXT PRIMARY KEY NOT NULL, conference_id TEXT NOT NULL REFERENCES conference_editions,
 legacy_topic_id TEXT NOT NULL, parent_topic_id TEXT REFERENCES research_topics,
 node_type TEXT NOT NULL CHECK(node_type IN('board','topic')), name TEXT NOT NULL,
 research_question TEXT, taxonomy_status TEXT NOT NULL CHECK(taxonomy_status='working_classification'),
 material_id TEXT NOT NULL REFERENCES source_materials, UNIQUE(conference_id,legacy_topic_id)
);
CREATE TABLE report_classifications (
 report_id TEXT NOT NULL REFERENCES reports, analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 primary_topic_id TEXT REFERENCES research_topics, scope_original TEXT NOT NULL,
 eligible INTEGER NOT NULL CHECK(eligible IN(0,1)), classification_basis TEXT NOT NULL,
 material_id TEXT NOT NULL REFERENCES source_materials, source_locator TEXT NOT NULL,
 PRIMARY KEY(report_id,analysis_version_id),
 CHECK((eligible=1 AND primary_topic_id IS NOT NULL) OR (eligible=0 AND primary_topic_id IS NULL))
);
CREATE TABLE report_tags (
 report_id TEXT NOT NULL REFERENCES reports, analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 tag TEXT NOT NULL, material_id TEXT NOT NULL REFERENCES source_materials,
 PRIMARY KEY(report_id,analysis_version_id,tag)
);
CREATE TABLE biomarker_title_reviews (
 report_id TEXT NOT NULL REFERENCES reports, analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 review_status TEXT NOT NULL, in_denominator INTEGER NOT NULL CHECK(in_denominator IN(0,1)),
 target_text TEXT, use_text TEXT, indicator_kind TEXT, basis TEXT NOT NULL,
 review_level TEXT NOT NULL, material_id TEXT NOT NULL REFERENCES source_materials,
 source_locator TEXT NOT NULL, PRIMARY KEY(report_id,analysis_version_id)
);
CREATE TABLE legacy_marker_bindings (
 report_id TEXT NOT NULL REFERENCES reports, analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 legacy_marker_id TEXT NOT NULL, evidence_id_original TEXT NOT NULL,
 binding_status TEXT NOT NULL CHECK(binding_status='existing_title_binding_pending_review'),
 material_id TEXT NOT NULL REFERENCES source_materials, source_locator TEXT NOT NULL,
 PRIMARY KEY(report_id,analysis_version_id,legacy_marker_id)
);
CREATE TABLE studies (
 study_id TEXT PRIMARY KEY NOT NULL, title TEXT, identity_status TEXT NOT NULL,
 doi TEXT, trial_registration TEXT, cohort_description TEXT,
 source_material_id TEXT NOT NULL REFERENCES source_materials
);
CREATE TABLE report_study_links (
 report_id TEXT NOT NULL REFERENCES reports, study_id TEXT NOT NULL REFERENCES studies,
 relation_type TEXT NOT NULL CHECK(relation_type IN('confirmed_same_study','possible_overlap','shared_cohort','pending')),
 basis TEXT NOT NULL, material_id TEXT NOT NULL REFERENCES source_materials,
 PRIMARY KEY(report_id,study_id,relation_type)
);
CREATE VIEW v_conference_inventory AS
 SELECT c.*, (SELECT COUNT(*) FROM sessions s WHERE s.conference_id=c.conference_id) AS session_count,
 (SELECT COUNT(*) FROM agenda_items a WHERE a.conference_id=c.conference_id) AS agenda_item_count,
 (SELECT COUNT(*) FROM reports r WHERE r.conference_id=c.conference_id) AS academic_report_count,
 'agenda_only' AS result_coverage FROM conference_editions c;
CREATE VIEW v_report_detail AS
 WITH p AS (SELECT ap.agenda_item_id,GROUP_CONCAT(pe.display_name||' ['||ap.institution_original||']','；') AS speaker_labels,
 COUNT(*) AS listed_person_count FROM agenda_participants ap JOIN people pe ON pe.person_id=ap.person_id
 WHERE ap.agenda_role='speaker' GROUP BY ap.agenda_item_id)
 SELECT r.*,a.session_id,a.title_original,a.format_original,a.local_date,a.time_original,a.start_time,a.end_time,
 a.room_original,a.source_url,a.material_id,a.source_locator,s.title_original AS session_title,
 m.relative_path AS material_path,COALESCE(p.listed_person_count,0) AS listed_speaker_count,p.speaker_labels
 FROM reports r JOIN agenda_items a ON a.agenda_item_id=r.agenda_item_id
 JOIN sessions s ON s.session_id=a.session_id JOIN source_materials m ON m.material_id=a.material_id
 LEFT JOIN p ON p.agenda_item_id=a.agenda_item_id;
CREATE VIEW v_topic_counts AS
 WITH base AS (SELECT rc.* FROM report_classifications rc JOIN analysis_versions av USING(analysis_version_id)
 WHERE av.is_current_snapshot=1 AND av.analysis_kind='primary_topic'),
 den AS (SELECT analysis_version_id,COUNT(DISTINCT report_id) AS denominator FROM base WHERE eligible=1 GROUP BY analysis_version_id)
 SELECT t.conference_id,b.analysis_version_id,t.topic_id,t.legacy_topic_id,t.name,t.parent_topic_id,
 COUNT(DISTINCT b.report_id) AS report_count,den.denominator,
 ROUND(100.0*COUNT(DISTINCT b.report_id)/NULLIF(den.denominator,0),2) AS report_share_percent
 FROM research_topics t JOIN base b ON b.primary_topic_id=t.topic_id AND b.eligible=1
 JOIN den ON den.analysis_version_id=b.analysis_version_id
 WHERE t.node_type='topic' GROUP BY t.conference_id,b.analysis_version_id,t.topic_id;
CREATE VIEW v_board_counts AS
 SELECT p.conference_id,v.analysis_version_id,p.topic_id,p.legacy_topic_id,p.name,
 SUM(v.report_count) AS report_count,MAX(v.denominator) AS denominator,
 ROUND(100.0*SUM(v.report_count)/NULLIF(MAX(v.denominator),0),2) AS report_share_percent
 FROM research_topics p JOIN v_topic_counts v ON v.parent_topic_id=p.topic_id
 WHERE p.node_type='board' GROUP BY p.topic_id,v.analysis_version_id;
CREATE VIEW v_leader_talks AS
 WITH roles AS (SELECT person_id,COUNT(*) AS claim_count,GROUP_CONCAT(role_phrase,'；') AS role_phrases,
 GROUP_CONCAT(DISTINCT role_level) AS role_levels FROM academic_role_claims GROUP BY person_id)
 SELECT DISTINCT r.conference_id,r.report_id,r.source_report_code,a.title_original AS report_title,
 a.local_date,a.time_original,a.format_original,p.person_id,p.legacy_person_id,p.display_name,p.institution_source,
 roles.role_levels,roles.role_phrases,roles.claim_count,ap.profile_url,a.source_url
 FROM reports r JOIN agenda_items a ON a.agenda_item_id=r.agenda_item_id
 JOIN agenda_participants ap ON ap.agenda_item_id=a.agenda_item_id AND ap.agenda_role='speaker'
 JOIN people p ON p.person_id=ap.person_id JOIN roles ON roles.person_id=p.person_id;
CREATE VIEW v_biomarker_title_scope AS
 SELECT r.conference_id,b.analysis_version_id,b.review_status,b.in_denominator,COUNT(*) AS report_count
 FROM biomarker_title_reviews b JOIN reports r USING(report_id)
 JOIN analysis_versions av USING(analysis_version_id) WHERE av.is_current_snapshot=1
 GROUP BY r.conference_id,b.analysis_version_id,b.review_status,b.in_denominator;
