-- 建议以只读方式打开数据库；以下均为SELECT。
-- 1. 会议目录：完整日程797条，学术报告606条。
SELECT * FROM v_conference_inventory;
-- 2. 原始类型分布，专题会发言等不混入学术报告。
SELECT format_original, COUNT(*) AS item_count FROM agenda_items GROUP BY format_original;
-- 3. 具体议题的报告数量和占比；不计算旧综合分。
SELECT legacy_topic_id,name,report_count,denominator,report_share_percent
FROM v_topic_counts ORDER BY report_count DESC,legacy_topic_id;
-- 4. 有来源角色的人正在讲什么。此处每行是“报告×人员”，不是独立研究数。
SELECT display_name,institution_source,role_levels,role_phrases,source_report_code,report_title,source_url
FROM v_leader_talks ORDER BY display_name,source_report_code;
-- 5. 标志物题名复核及待细分清单。
SELECT * FROM v_biomarker_title_scope;
SELECT r.source_report_code,a.title_original,b.target_text,b.use_text,b.basis
FROM biomarker_title_reviews b JOIN reports r USING(report_id)
JOIN agenda_items a ON a.agenda_item_id=r.agenda_item_id
WHERE b.in_denominator=1 AND b.report_id NOT IN(SELECT report_id FROM legacy_marker_bindings);
-- 6. 讲者简介的真实读取范围，失败入口仍保留。
SELECT read_status,COUNT(*) AS profile_records,SUM(has_substantive_bio) AS substantive_bios
FROM person_profiles GROUP BY read_status;
-- 7. 研究身份未确立：应为0项，不把606条会前报告灌成606项研究。
SELECT COUNT(*) AS established_study_records FROM studies;
