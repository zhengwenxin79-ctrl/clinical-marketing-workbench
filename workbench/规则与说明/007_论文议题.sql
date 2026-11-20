CREATE TABLE IF NOT EXISTS literature_issue_versions (
 version_id TEXT PRIMARY KEY, created_on TEXT NOT NULL, input_sha256 TEXT NOT NULL,
 review_scope TEXT NOT NULL, input_count INTEGER NOT NULL, is_current INTEGER NOT NULL,
 evidence_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_issues (
 issue_id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES literature_issue_versions,
 board_id TEXT NOT NULL REFERENCES research_topics, name TEXT NOT NULL,
 boundary_text TEXT NOT NULL, progress_summary TEXT NOT NULL,
 limits_text TEXT NOT NULL, width_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_issue_paper_reviews (
 version_id TEXT NOT NULL REFERENCES literature_issue_versions,
 paper_id TEXT NOT NULL REFERENCES literature_papers,
 reviewed_type TEXT NOT NULL, evidence_kind TEXT NOT NULL,
 finding_summary TEXT NOT NULL, method_excerpt TEXT NOT NULL, result_excerpt TEXT NOT NULL,
 review_basis TEXT NOT NULL, original_board_id TEXT REFERENCES research_topics,
 review_status TEXT NOT NULL, evidence_path TEXT NOT NULL,
 PRIMARY KEY(version_id,paper_id)
);
CREATE TABLE IF NOT EXISTS literature_issue_links (
 version_id TEXT NOT NULL REFERENCES literature_issue_versions,
 issue_id TEXT NOT NULL REFERENCES literature_issues,
 paper_id TEXT NOT NULL REFERENCES literature_papers,
 relation TEXT NOT NULL CHECK(relation IN('primary','background','supporting')),
 count_in_ranking INTEGER NOT NULL CHECK(count_in_ranking IN(0,1)),
 basis TEXT NOT NULL,
 PRIMARY KEY(version_id,issue_id,paper_id),
 CHECK((relation='primary' AND count_in_ranking=1) OR (relation<>'primary' AND count_in_ranking=0))
);
CREATE UNIQUE INDEX IF NOT EXISTS literature_one_primary_issue ON literature_issue_links(version_id,paper_id) WHERE count_in_ranking=1;
CREATE VIEW IF NOT EXISTS v_literature_issue_counts AS
 SELECT i.*,t.name AS board_name,COUNT(DISTINCT CASE WHEN l.count_in_ranking=1 THEN l.paper_id END) AS paper_count,
 COUNT(DISTINCT CASE WHEN l.count_in_ranking=1 THEN p.journal END) AS journal_count,
 COUNT(DISTINCT CASE WHEN l.count_in_ranking=0 THEN l.paper_id END) AS supporting_count
 FROM literature_issues i JOIN literature_issue_versions v USING(version_id)
 JOIN research_topics t ON t.topic_id=i.board_id
 LEFT JOIN literature_issue_links l ON l.issue_id=i.issue_id AND l.version_id=i.version_id
 LEFT JOIN literature_papers p ON p.paper_id=l.paper_id WHERE v.is_current=1 GROUP BY i.issue_id;
