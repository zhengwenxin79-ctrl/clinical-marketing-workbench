CREATE TABLE IF NOT EXISTS tier_rule_versions (
 rule_version_id TEXT PRIMARY KEY NOT NULL,
 label TEXT NOT NULL,
 assessed_on TEXT NOT NULL,
 source_snapshot_date TEXT NOT NULL,
 rule_path TEXT NOT NULL,
 rule_sha256 TEXT NOT NULL,
 decisions_path TEXT NOT NULL,
 decisions_sha256 TEXT NOT NULL,
 assessment_method TEXT NOT NULL,
 current_snapshot INTEGER NOT NULL CHECK(current_snapshot IN(0,1)),
 new_collection INTEGER NOT NULL CHECK(new_collection=0)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_current_tier_rule ON tier_rule_versions(current_snapshot) WHERE current_snapshot=1;
CREATE TABLE IF NOT EXISTS speaker_tier_assignments (
 conference_id TEXT NOT NULL REFERENCES conference_editions,
 person_id TEXT NOT NULL REFERENCES people,
 rule_version_id TEXT NOT NULL REFERENCES tier_rule_versions,
 tier_code TEXT NOT NULL CHECK(tier_code IN('international','national','regional','undetermined')),
 domain_scope TEXT,
 assessment_status TEXT NOT NULL CHECK(assessment_status IN('provisional_existing_bio','insufficient_evidence')),
 tenure_status TEXT NOT NULL CHECK(tenure_status IN('term_unverified','historical','honorary','chair_elect','dated_term_unverified','not_applicable')),
 rationale TEXT NOT NULL,
 evidence_gaps TEXT NOT NULL,
 PRIMARY KEY(conference_id,person_id,rule_version_id),
 CHECK((tier_code='undetermined' AND assessment_status='insufficient_evidence') OR (tier_code<>'undetermined' AND assessment_status='provisional_existing_bio'))
);
CREATE TABLE IF NOT EXISTS speaker_tier_evidence (
 evidence_id TEXT PRIMARY KEY NOT NULL,
 conference_id TEXT NOT NULL,
 person_id TEXT NOT NULL,
 rule_version_id TEXT NOT NULL,
 profile_id TEXT NOT NULL REFERENCES person_profiles,
 source_material_id TEXT NOT NULL REFERENCES source_materials,
 source_locator TEXT NOT NULL,
 quote_original TEXT NOT NULL,
 context_original TEXT NOT NULL,
 char_start INTEGER NOT NULL,
 char_end INTEGER NOT NULL,
 evidence_kind TEXT NOT NULL,
 FOREIGN KEY(conference_id,person_id,rule_version_id) REFERENCES speaker_tier_assignments,
 CHECK(char_start>=0 AND char_end>char_start)
);
CREATE TABLE IF NOT EXISTS conference_tier_assignments (
 conference_id TEXT NOT NULL REFERENCES conference_editions,
 rule_version_id TEXT NOT NULL REFERENCES tier_rule_versions,
 tier_code TEXT NOT NULL CHECK(tier_code IN('international_core','national_major','regional_key','undetermined')),
 scope_label TEXT NOT NULL,
 assessment_status TEXT NOT NULL CHECK(assessment_status IN('user_confirmed','provisional','insufficient_evidence')),
 basis_type TEXT NOT NULL,
 basis_text TEXT NOT NULL,
 source_material_id TEXT REFERENCES source_materials,
 source_locator TEXT,
 evidence_gaps TEXT NOT NULL,
 PRIMARY KEY(conference_id,rule_version_id)
);
CREATE VIEW IF NOT EXISTS v_speaker_tiers AS
 SELECT a.*,p.display_name,p.institution_source,
 CASE a.tier_code WHEN 'international' THEN '国际学术带头人' WHEN 'national' THEN '全国学术带头人' WHEN 'regional' THEN '区域／专科学术带头人' ELSE '层级待定' END AS tier_label,
 (SELECT COUNT(*) FROM speaker_tier_evidence e WHERE e.conference_id=a.conference_id AND e.person_id=a.person_id AND e.rule_version_id=a.rule_version_id) AS evidence_count
 FROM speaker_tier_assignments a JOIN people p USING(person_id) JOIN tier_rule_versions v USING(rule_version_id)
 WHERE v.current_snapshot=1;
CREATE VIEW IF NOT EXISTS v_speaker_tier_counts AS
 SELECT conference_id,tier_code,tier_label,COUNT(*) AS identity_count FROM v_speaker_tiers GROUP BY conference_id,tier_code,tier_label;
CREATE VIEW IF NOT EXISTS v_conference_tiers AS
 SELECT a.*,CASE a.tier_code WHEN 'international_core' THEN '国际核心会议' WHEN 'national_major' THEN '国内全国性大型会议' WHEN 'regional_key' THEN '区域重点会议' ELSE '层级待定' END AS tier_label
 FROM conference_tier_assignments a JOIN tier_rule_versions v USING(rule_version_id) WHERE v.current_snapshot=1;
CREATE VIEW IF NOT EXISTS v_tier_speaker_talks AS
 SELECT DISTINCT t.conference_id,t.person_id,t.display_name,t.institution_source,t.tier_code,t.tier_label,t.domain_scope,t.assessment_status,t.tenure_status,
 r.report_id,r.source_report_code,r.title_original,r.local_date,r.time_original,r.report_format,r.source_url
 FROM v_speaker_tiers t JOIN agenda_participants ap USING(person_id) JOIN v_report_detail r USING(agenda_item_id)
 WHERE ap.agenda_role='speaker' AND r.conference_id=t.conference_id;
PRAGMA user_version=2;
