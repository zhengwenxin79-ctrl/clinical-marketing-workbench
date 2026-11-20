CREATE TABLE conference_coverage (
 conference_id TEXT PRIMARY KEY REFERENCES conference_editions,
 analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 programme_material_id TEXT NOT NULL REFERENCES source_materials,
 programme_text_material_id TEXT NOT NULL REFERENCES source_materials,
 source_snapshot_label TEXT NOT NULL,
 original_observed_on TEXT NOT NULL,
 coverage_json TEXT NOT NULL CHECK(json_valid(coverage_json)),
 rules_path TEXT NOT NULL, rules_sha256 TEXT NOT NULL,
 plan_path TEXT NOT NULL, plan_sha256 TEXT NOT NULL,
 gaps TEXT NOT NULL,
 new_collection INTEGER NOT NULL CHECK(new_collection=0)
);
CREATE TABLE conference_program_occurrences (
 report_id TEXT NOT NULL REFERENCES reports,
 agenda_item_id TEXT NOT NULL UNIQUE REFERENCES agenda_items,
 programme_pages TEXT NOT NULL CHECK(json_valid(programme_pages)),
 is_primary INTEGER NOT NULL CHECK(is_primary IN(0,1)),
 PRIMARY KEY(report_id,agenda_item_id)
);
CREATE TABLE conference_topic_scope (
 topic_id TEXT PRIMARY KEY REFERENCES research_topics,
 analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 template_topic_id TEXT REFERENCES research_topics,
 width_status TEXT NOT NULL CHECK(width_status IN('focused','broad')),
 boundary_text TEXT NOT NULL,
 evidence_gaps TEXT NOT NULL
);
CREATE TABLE conference_report_notes (
 report_id TEXT NOT NULL REFERENCES reports,
 analysis_version_id TEXT NOT NULL REFERENCES analysis_versions,
 classification_method TEXT NOT NULL,
 classification_basis TEXT NOT NULL,
 evidence_gaps TEXT NOT NULL,
 cross_tags_json TEXT NOT NULL CHECK(json_valid(cross_tags_json)),
 PRIMARY KEY(report_id,analysis_version_id)
);
CREATE TABLE conference_page_audit (
 conference_id TEXT NOT NULL REFERENCES conference_editions,
 physical_page INTEGER NOT NULL,
 parse_status TEXT NOT NULL,
 code_occurrences INTEGER NOT NULL,
 PRIMARY KEY(conference_id,physical_page)
);
CREATE TABLE curated_research_records (
 record_id TEXT PRIMARY KEY,conference_id TEXT NOT NULL REFERENCES conference_editions,
 legacy_id TEXT NOT NULL,code_original TEXT NOT NULL,title_curated TEXT NOT NULL,
 evidence_level TEXT NOT NULL,reading_level TEXT NOT NULL,source_date TEXT,
 source_material_id TEXT NOT NULL REFERENCES source_materials,
 source_locator TEXT NOT NULL,raw_json TEXT NOT NULL CHECK(json_valid(raw_json))
);
CREATE TABLE curated_report_links (
 record_id TEXT NOT NULL REFERENCES curated_research_records,
 report_id TEXT NOT NULL REFERENCES reports,
 relation_type TEXT NOT NULL,basis TEXT NOT NULL,
 PRIMARY KEY(record_id,report_id)
);
CREATE TABLE related_paper_abstracts (
 paper_id TEXT PRIMARY KEY,pmid TEXT UNIQUE NOT NULL,doi TEXT,title_original TEXT NOT NULL,
 journal TEXT,first_author TEXT,source_url TEXT NOT NULL,reading_level TEXT NOT NULL,
 source_material_id TEXT NOT NULL REFERENCES source_materials,
 source_locator TEXT NOT NULL,raw_json TEXT NOT NULL CHECK(json_valid(raw_json))
);
CREATE TABLE related_paper_links (
 record_id TEXT NOT NULL REFERENCES curated_research_records,
 paper_id TEXT NOT NULL REFERENCES related_paper_abstracts,
 relation_type TEXT NOT NULL,basis TEXT NOT NULL,
 PRIMARY KEY(record_id,paper_id)
);
CREATE VIEW v_ada_quantity_topic_counts AS
 WITH base AS (
 SELECT rc.* FROM report_classifications rc JOIN analysis_versions av USING(analysis_version_id)
 WHERE av.analysis_kind='ada_topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=1
 ), den AS (SELECT analysis_version_id,COUNT(DISTINCT report_id) AS denominator FROM base GROUP BY analysis_version_id),
 cnt AS (
 SELECT t.conference_id,b.analysis_version_id,t.topic_id,t.legacy_topic_id,t.name,t.parent_topic_id,
 COUNT(DISTINCT b.report_id) AS report_count,den.denominator,
 ROUND(100.0*COUNT(DISTINCT b.report_id)/NULLIF(den.denominator,0),2) AS report_share_percent
 FROM research_topics t JOIN base b ON b.primary_topic_id=t.topic_id JOIN den USING(analysis_version_id)
 GROUP BY t.topic_id,b.analysis_version_id
 )
 SELECT c.*,DENSE_RANK() OVER(ORDER BY report_count DESC) AS quantity_rank,
 s.width_status,s.boundary_text,s.evidence_gaps AS scope_gaps,s.template_topic_id AS definition_origin_id
 FROM cnt c JOIN conference_topic_scope s USING(topic_id,analysis_version_id);
CREATE VIEW v_ada_quantity_board_counts AS
 SELECT p.conference_id,v.analysis_version_id,p.topic_id,p.legacy_topic_id,p.name,
 SUM(v.report_count) AS report_count,MAX(v.denominator) AS denominator,
 ROUND(100.0*SUM(v.report_count)/NULLIF(MAX(v.denominator),0),2) AS report_share_percent
 FROM research_topics p JOIN v_ada_quantity_topic_counts v ON v.parent_topic_id=p.topic_id
 GROUP BY p.topic_id,v.analysis_version_id;
CREATE VIEW v_ada_quantity_speaker_talks AS
 SELECT DISTINCT rc.primary_topic_id AS topic_id,rc.analysis_version_id,t.conference_id,t.person_id,t.display_name,t.institution_source,
 t.tier_code,t.tier_label,t.domain_scope,t.assessment_status,t.tenure_status,
 r.report_id,r.source_report_code,r.title_original,r.local_date,r.time_original,r.report_format,r.source_url
 FROM v_report_detail r JOIN report_classifications rc USING(report_id) JOIN analysis_versions av USING(analysis_version_id)
 JOIN conference_program_occurrences o USING(report_id) JOIN agenda_participants ap ON ap.agenda_item_id=o.agenda_item_id
 JOIN v_speaker_tiers t ON t.person_id=ap.person_id AND t.conference_id=r.conference_id
 WHERE av.analysis_kind='ada_topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=1 AND ap.agenda_role='speaker';
CREATE VIEW v_ada_quantity_topic_facts AS
 WITH base AS (
 SELECT r.*,rc.primary_topic_id AS topic_id FROM v_report_detail r JOIN report_classifications rc USING(report_id)
 JOIN analysis_versions av USING(analysis_version_id)
 WHERE av.analysis_kind='ada_topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=1
 ), agenda AS (
 SELECT topic_id,COUNT(*) AS report_count,SUM(report_format='大会报告') AS plenary_count,
 SUM(report_format='专题报告') AS invited_count,SUM(report_format='论文发言') AS oral_count,
 SUM(report_format='海报报告') AS poster_count,SUM(report_format='晚期突破海报') AS late_poster_count,
 SUM(NOT EXISTS(SELECT 1 FROM conference_program_occurrences o JOIN agenda_participants ap ON ap.agenda_item_id=o.agenda_item_id WHERE o.report_id=b.report_id AND ap.agenda_role='speaker')) AS reports_without_speaker
 FROM base b GROUP BY topic_id
 ), sessions AS (
 SELECT b.topic_id,COUNT(DISTINCT a.session_id) AS session_count FROM base b JOIN conference_program_occurrences o USING(report_id)
 JOIN agenda_items a ON a.agenda_item_id=o.agenda_item_id GROUP BY b.topic_id
 ), persons AS (
 SELECT DISTINCT b.topic_id,ap.person_id,COALESCE(t.tier_code,'undetermined') AS tier_code
 FROM base b JOIN conference_program_occurrences o USING(report_id) JOIN agenda_participants ap ON ap.agenda_item_id=o.agenda_item_id
 LEFT JOIN v_speaker_tiers t ON t.person_id=ap.person_id AND t.conference_id=b.conference_id WHERE ap.agenda_role='speaker'
 ), pc AS (
 SELECT topic_id,COUNT(*) AS speaker_identity_count,SUM(tier_code='international') AS international_count,
 SUM(tier_code='national') AS national_count,SUM(tier_code='regional') AS regional_count,SUM(tier_code='undetermined') AS undetermined_count,
 SUM(EXISTS(SELECT 1 FROM person_profiles pr WHERE pr.person_id=persons.person_id AND pr.has_substantive_bio=1)) AS speaker_bio_count
 FROM persons GROUP BY topic_id
 )
 SELECT a.*,s.session_count,COALESCE(p.speaker_identity_count,0) AS speaker_identity_count,COALESCE(p.international_count,0) AS international_count,
 COALESCE(p.national_count,0) AS national_count,COALESCE(p.regional_count,0) AS regional_count,COALESCE(p.undetermined_count,0) AS undetermined_count,
 COALESCE(p.speaker_bio_count,0) AS speaker_bio_count FROM agenda a JOIN sessions s USING(topic_id) LEFT JOIN pc p USING(topic_id);
PRAGMA user_version=5;
