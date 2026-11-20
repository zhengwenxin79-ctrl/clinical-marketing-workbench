-- 当前数量榜：同数量并列；不将人物或专题数加入排序。
SELECT name,report_count,report_share_percent,quantity_rank,width_status
FROM v_cds_quantity_topic_counts ORDER BY report_count DESC,legacy_topic_id;
-- 可只看边界较集中的议题，分母仍579。
SELECT name,report_count,report_share_percent,quantity_rank
FROM v_cds_quantity_topic_counts WHERE width_status='focused'
ORDER BY report_count DESC,legacy_topic_id;
-- 原始分项事实。
SELECT * FROM v_cds_quantity_topic_facts WHERE topic_id='CDS2026:Q33A';
-- 哪些已分层讲者在讨论什么；角色领域及任期不可省略。
SELECT tier_label,display_name,domain_scope,tenure_status,source_report_code,title_original,source_url
FROM v_cds_quantity_speaker_talks
WHERE topic_id='CDS2026:Q33A' AND tier_code<>'undetermined'
ORDER BY display_name,source_report_code;
-- 某报告调整前后的归类依据与缺口。
SELECT n.report_id,n.previous_topic_id,rc.primary_topic_id,n.decision_code,n.rationale,n.evidence_gaps
FROM report_topic_review_notes n JOIN report_classifications rc
ON rc.report_id=n.report_id AND rc.analysis_version_id=n.analysis_version_id
WHERE n.report_id='CDS2026:OR_101';
-- 旧44议题仍可查，不与新分类混合加总。
SELECT name,report_count FROM v_topic_counts ORDER BY report_count DESC;
