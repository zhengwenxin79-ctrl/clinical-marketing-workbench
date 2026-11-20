CREATE TABLE IF NOT EXISTS literature_runs (
 run_id TEXT PRIMARY KEY, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
 collected_on TEXT NOT NULL, manifest_path TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
 scope_note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_sources (
 source_id TEXT PRIMARY KEY, label TEXT NOT NULL, source_kind TEXT NOT NULL,
 source_url TEXT NOT NULL, coverage_status TEXT NOT NULL, coverage_note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_source_checks (
 run_id TEXT NOT NULL REFERENCES literature_runs, source_id TEXT NOT NULL REFERENCES literature_sources,
 query_text TEXT, returned_count INTEGER, reading_status TEXT NOT NULL, gaps TEXT NOT NULL,
 raw_path TEXT NOT NULL, PRIMARY KEY(run_id,source_id)
);
CREATE TABLE IF NOT EXISTS literature_papers (
 paper_id TEXT PRIMARY KEY, pmid TEXT UNIQUE, doi TEXT UNIQUE, pmcid TEXT,
 title TEXT NOT NULL, journal TEXT NOT NULL, journal_abbr TEXT,
 publication_date TEXT, date_precision TEXT, date_basis TEXT NOT NULL,
 online_date TEXT, issue_date TEXT, window_status TEXT NOT NULL,
 source_tier TEXT NOT NULL, article_type TEXT NOT NULL, type_basis TEXT NOT NULL,
 reading_level TEXT NOT NULL, abstract_json TEXT NOT NULL CHECK(json_valid(abstract_json)),
 summary_curated TEXT, source_url TEXT NOT NULL, publisher_url TEXT,
 raw_path TEXT NOT NULL, source_locator TEXT NOT NULL,
 existing_abstract_id TEXT REFERENCES related_paper_abstracts,
 run_id TEXT NOT NULL REFERENCES literature_runs
);
CREATE TABLE IF NOT EXISTS literature_authors (
 paper_id TEXT NOT NULL REFERENCES literature_papers, ordinal INTEGER NOT NULL,
 name_original TEXT NOT NULL, affiliations_json TEXT NOT NULL CHECK(json_valid(affiliations_json)),
 orcid TEXT, is_collective INTEGER NOT NULL, corresponding_status TEXT NOT NULL,
 PRIMARY KEY(paper_id,ordinal)
);
CREATE TABLE IF NOT EXISTS literature_classifications (
 paper_id TEXT PRIMARY KEY REFERENCES literature_papers,
 board_id TEXT REFERENCES research_topics, scope_status TEXT NOT NULL,
 classification_basis TEXT NOT NULL, review_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_people (
 person_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, domain_scope TEXT NOT NULL,
 identity_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_person_roles (
 person_id TEXT PRIMARY KEY REFERENCES literature_people,
 tier_code TEXT NOT NULL CHECK(tier_code IN('international','national','regional','undetermined')),
 academy_kind TEXT, role_basis TEXT NOT NULL, source_url TEXT NOT NULL,
 tenure_note TEXT NOT NULL, raw_path TEXT NOT NULL, checked_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_author_links (
 paper_id TEXT NOT NULL, ordinal INTEGER NOT NULL, person_id TEXT NOT NULL REFERENCES literature_people,
 identity_status TEXT NOT NULL, article_role TEXT NOT NULL,
 leadership_status TEXT NOT NULL CHECK(leadership_status IN('paper_leadership_pending','corresponding_verified','pi_verified')),
 matching_basis TEXT NOT NULL,
 PRIMARY KEY(paper_id,ordinal,person_id),
 FOREIGN KEY(paper_id,ordinal) REFERENCES literature_authors(paper_id,ordinal)
);
CREATE TABLE IF NOT EXISTS literature_highlights (
 paper_id TEXT PRIMARY KEY REFERENCES literature_papers,
 research_question TEXT NOT NULL, finding_summary TEXT NOT NULL,
 selection_reason TEXT NOT NULL, limits_text TEXT NOT NULL,
 review_status TEXT NOT NULL, raw_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS literature_discovery_candidates (
 run_id TEXT NOT NULL REFERENCES literature_runs, pmid TEXT NOT NULL,
 reading_status TEXT NOT NULL, PRIMARY KEY(run_id,pmid)
);
CREATE VIEW IF NOT EXISTS v_literature_pool AS
 SELECT p.*,c.board_id,t.name AS board_name,c.scope_status,c.classification_basis,c.review_status,
 CASE WHEN p.window_status='in_window'
      AND p.source_tier='core' AND p.article_type IN('original_indexed','original_candidate','original_reviewed')
      AND c.scope_status IN('direct','related_metabolic') AND c.board_id IS NOT NULL THEN 1 ELSE 0 END AS in_core_counts
 FROM literature_papers p JOIN literature_classifications c USING(paper_id)
 LEFT JOIN research_topics t ON c.board_id=t.topic_id;
CREATE VIEW IF NOT EXISTS v_literature_board_counts AS
 SELECT board_id,board_name,COUNT(*) AS paper_count,
 SUM(article_type='original_candidate') AS original_type_pending_count
 FROM v_literature_pool WHERE in_core_counts=1 GROUP BY board_id,board_name;
