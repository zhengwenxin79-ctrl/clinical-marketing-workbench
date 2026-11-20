CREATE TABLE IF NOT EXISTS quantity_rule_versions (
 analysis_version_id TEXT PRIMARY KEY NOT NULL REFERENCES analysis_versions,
 previous_analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 reviewed_on TEXT NOT NULL,
 rules_path TEXT NOT NULL,rules_sha256 TEXT NOT NULL,
 decisions_path TEXT NOT NULL,decisions_sha256 TEXT NOT NULL,
 review_method TEXT NOT NULL,denominator INTEGER NOT NULL,
 new_collection INTEGER NOT NULL CHECK(new_collection=0),
 scoring_enabled INTEGER NOT NULL CHECK(scoring_enabled=0)
);
CREATE TABLE IF NOT EXISTS topic_scope_reviews (
 analysis_version_id TEXT NOT NULL REFERENCES quantity_rule_versions,
 old_topic_id TEXT NOT NULL REFERENCES research_topics,
 old_report_count INTEGER NOT NULL,
 action TEXT NOT NULL CHECK(action IN('split','retain_broad','retain')),
 rationale TEXT NOT NULL,evidence_gaps TEXT NOT NULL,
 PRIMARY KEY(analysis_version_id,old_topic_id)
);
CREATE TABLE IF NOT EXISTS topic_scope_review_targets (
 analysis_version_id TEXT NOT NULL,
 old_topic_id TEXT NOT NULL,
 new_topic_id TEXT NOT NULL REFERENCES research_topics,
 width_status TEXT NOT NULL CHECK(width_status IN('broad','focused')),
 boundary_text TEXT NOT NULL,evidence_gaps TEXT NOT NULL,
 PRIMARY KEY(analysis_version_id,old_topic_id,new_topic_id),
 FOREIGN KEY(analysis_version_id,old_topic_id) REFERENCES topic_scope_reviews
);
CREATE TABLE IF NOT EXISTS report_topic_review_notes (
 analysis_version_id TEXT NOT NULL REFERENCES quantity_rule_versions,
 report_id TEXT NOT NULL REFERENCES reports,
 previous_topic_id TEXT REFERENCES research_topics,
 decision_code TEXT NOT NULL CHECK(decision_code IN('retain','split_assignment','reassign','excluded')),
 rationale TEXT NOT NULL,evidence_gaps TEXT NOT NULL,
 source_material_id TEXT NOT NULL REFERENCES source_materials,
 source_locator TEXT NOT NULL,
 PRIMARY KEY(analysis_version_id,report_id),
 FOREIGN KEY(report_id,analysis_version_id) REFERENCES report_classifications(report_id,analysis_version_id)
);
CREATE VIEW IF NOT EXISTS v_cds_quantity_topic_counts AS
 WITH base AS (
  SELECT rc.* FROM report_classifications rc JOIN analysis_versions av USING(analysis_version_id)
  WHERE av.analysis_kind='topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=1
 ), den AS (SELECT analysis_version_id,COUNT(DISTINCT report_id) AS denominator FROM base GROUP BY analysis_version_id),
 counts AS (
  SELECT t.conference_id,b.analysis_version_id,t.topic_id,t.legacy_topic_id,t.name,t.parent_topic_id,
   COUNT(DISTINCT b.report_id) AS report_count,den.denominator,
   ROUND(100.0*COUNT(DISTINCT b.report_id)/NULLIF(den.denominator,0),2) AS report_share_percent
  FROM research_topics t JOIN base b ON b.primary_topic_id=t.topic_id JOIN den USING(analysis_version_id)
  GROUP BY t.conference_id,b.analysis_version_id,t.topic_id
 )
 SELECT c.*,DENSE_RANK() OVER(PARTITION BY conference_id ORDER BY report_count DESC) AS quantity_rank,
  x.width_status,x.boundary_text,x.evidence_gaps AS scope_gaps,x.old_topic_id AS definition_origin_id
 FROM counts c JOIN topic_scope_review_targets x ON x.analysis_version_id=c.analysis_version_id AND x.new_topic_id=c.topic_id;
CREATE VIEW IF NOT EXISTS v_cds_quantity_board_counts AS
 SELECT p.conference_id,v.analysis_version_id,p.topic_id,p.legacy_topic_id,p.name,
 SUM(v.report_count) AS report_count,MAX(v.denominator) AS denominator,
 ROUND(100.0*SUM(v.report_count)/NULLIF(MAX(v.denominator),0),2) AS report_share_percent
 FROM research_topics p JOIN v_cds_quantity_topic_counts v ON v.parent_topic_id=p.topic_id GROUP BY p.topic_id,v.analysis_version_id;
CREATE VIEW IF NOT EXISTS v_cds_quantity_speaker_talks AS
 SELECT rc.primary_topic_id AS topic_id,rc.analysis_version_id,t.*
 FROM v_tier_speaker_talks t JOIN report_classifications rc USING(report_id)
 JOIN analysis_versions av USING(analysis_version_id)
 WHERE av.analysis_kind='topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=1;
CREATE VIEW IF NOT EXISTS v_cds_quantity_topic_facts AS
 WITH base AS (
  SELECT r.*,rc.primary_topic_id AS topic_id,rc.analysis_version_id FROM v_report_detail r
  JOIN report_classifications rc USING(report_id) JOIN analysis_versions av USING(analysis_version_id)
  WHERE av.analysis_kind='topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=1
 ), agenda AS (
  SELECT topic_id,COUNT(DISTINCT report_id) AS report_count,COUNT(DISTINCT session_id) AS session_count,
  SUM(report_format='大会报告') AS plenary_count,SUM(report_format='专题报告') AS invited_count,
  SUM(report_format='论文发言') AS oral_count,SUM(listed_speaker_count=0) AS reports_without_speaker
  FROM base GROUP BY topic_id
 ), persons AS (
  SELECT DISTINCT b.topic_id,ap.person_id,COALESCE(st.tier_code,'undetermined') AS tier_code
  FROM base b JOIN agenda_participants ap USING(agenda_item_id)
  LEFT JOIN v_speaker_tiers st ON st.person_id=ap.person_id AND st.conference_id=b.conference_id
  WHERE ap.agenda_role='speaker'
 ), pc AS (
  SELECT topic_id,COUNT(*) AS speaker_identity_count,
  SUM(tier_code='international') AS international_count,SUM(tier_code='national') AS national_count,
  SUM(tier_code='regional') AS regional_count,SUM(tier_code='undetermined') AS undetermined_count,
  SUM(EXISTS(SELECT 1 FROM person_profiles pr WHERE pr.person_id=persons.person_id AND pr.read_status='read' AND pr.has_substantive_bio=1)) AS speaker_bio_count
  FROM persons GROUP BY topic_id
 )
 SELECT a.*,COALESCE(p.speaker_identity_count,0) AS speaker_identity_count,
 COALESCE(p.international_count,0) AS international_count,COALESCE(p.national_count,0) AS national_count,
 COALESCE(p.regional_count,0) AS regional_count,COALESCE(p.undetermined_count,0) AS undetermined_count,
 COALESCE(p.speaker_bio_count,0) AS speaker_bio_count
 FROM agenda a LEFT JOIN pc p USING(topic_id);
PRAGMA user_version=3;
