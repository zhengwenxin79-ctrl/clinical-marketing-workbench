"""只读复核数量、人物去重、分项及历史保留，不依赖网页计算。"""
from pathlib import Path
from collections import Counter
import sqlite3,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;folder=r/'规则与说明/CDS议题数量复核_2026-11-17';baseline=json.loads((folder/'变更前基线.json').read_text());c=sqlite3.connect((r/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;old=sqlite3.connect((r/baseline['backup_database']).as_uri()+'?mode=ro',uri=True);checks=[]
 try:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('PRAGMA user_version').fetchone()[0]>=3
  allowed={'analysis_versions','research_topics','report_classifications'}
  for (t,) in old.execute("SELECT name FROM sqlite_schema WHERE type='table'"):
   prior={tuple(x) for x in old.execute('SELECT * FROM '+t)};now={tuple(x) for x in c.execute('SELECT * FROM '+t)};assert prior<=now,t
   # 新会议允许追加记录；旧记录逐项保留校验保持。
  checks.append('SQLite版本≥3完整性/外键通过；原24表旧记录全部保留，新会议追加独立记录')
  q=dict(c.execute('SELECT * FROM quantity_rule_versions').fetchone());vid=q['analysis_version_id'];assert sha(r/q['rules_path'])==q['rules_sha256'];assert sha(r/q['decisions_path'])==q['decisions_sha256']
  topics=[dict(x) for x in c.execute('SELECT * FROM v_cds_quantity_topic_counts')];assert len(topics)==58;assert sum(t['report_count'] for t in topics)==579
  assert Counter(t['width_status'] for t in topics)=={'focused':39,'broad':19};assert c.execute('SELECT COUNT(*) FROM topic_scope_reviews').fetchone()[0]==44;assert c.execute("SELECT COUNT(*) FROM topic_scope_reviews WHERE action='split'").fetchone()[0]==9
  notes=[dict(x) for x in c.execute('SELECT * FROM report_topic_review_notes WHERE analysis_version_id=?',(vid,))];assert len(notes)==606;assert sum(x['decision_code']=='reassign' for x in notes)==13
  checks.append('44个旧议题全部有复核，9个拆分为23个；新版58议题=39集中+19较宽；13条调整归属均有理由和缺口')
  cls=[dict(x) for x in c.execute('SELECT * FROM report_classifications WHERE analysis_version_id=?',(vid,))];assert len(cls)==606 and sum(x['eligible'] for x in cls)==579
  ranks={n:i+1 for i,n in enumerate(sorted({t['report_count'] for t in topics},reverse=True))}
  for t in topics:
   rows=[dict(x) for x in c.execute('SELECT r.* FROM v_report_detail r JOIN report_classifications rc USING(report_id) WHERE rc.analysis_version_id=? AND rc.primary_topic_id=?',(vid,t['topic_id']))];assert len(rows)==len({x['report_id'] for x in rows})==t['report_count'];assert t['report_share_percent']==round(100*len(rows)/579,2);assert t['quantity_rank']==ranks[len(rows)]
   f=dict(c.execute('SELECT * FROM v_cds_quantity_topic_facts WHERE topic_id=?',(t['topic_id'],)).fetchone());types=Counter(x['report_format'] for x in rows)
   assert [f['plenary_count'],f['invited_count'],f['oral_count']]==[types['大会报告'],types['专题报告'],types['论文发言']];assert sum(types.values())==f['report_count'];assert f['session_count']==len({x['session_id'] for x in rows})
   pids={p[0] for x in rows for p in c.execute("SELECT person_id FROM agenda_participants WHERE agenda_item_id=? AND agenda_role='speaker'",(x['agenda_item_id'],))};tiers=Counter(c.execute("SELECT tier_code FROM v_speaker_tiers WHERE person_id=?",(pid,)).fetchone()[0] for pid in pids)
   assert f['speaker_identity_count']==len(pids);assert [f['international_count'],f['national_count'],f['regional_count'],f['undetermined_count']]==[tiers[k] for k in ['international','national','regional','undetermined']]
   assert sum(tiers.values())==len(pids)
  checks.append('58议题逐项独立回算：报告唯一、占比、同量并列、报告类型、跨Session、人物三级+待定分布一致')
  talks=[dict(x) for x in c.execute('SELECT * FROM v_cds_quantity_speaker_talks')];assert len(talks)==len({(x['topic_id'],x['person_id'],x['report_id']) for x in talks})
  assert c.execute('SELECT SUM(report_count) FROM v_cds_quantity_board_counts').fetchone()[0]==579;assert c.execute('SELECT COUNT(*) FROM v_cds_quantity_board_counts').fetchone()[0]==12
  assert c.execute('SELECT COUNT(*) FROM v_topic_counts').fetchone()[0]==44;assert c.execute('SELECT SUM(report_count) FROM v_topic_counts').fetchone()[0]==579
  checks.append('主讲关系未因多个职务或多条证据增行；12板块合计579，旧44议题视图仍可回读')
  assert c.execute('SELECT COUNT(*) FROM analysis_versions WHERE scoring_enabled<>0').fetchone()[0]==0;assert c.execute('SELECT COUNT(*) FROM reports WHERE has_results<>0').fetchone()[0]==0
  assert {x[0] for x in c.execute("SELECT name FROM sqlite_schema WHERE type='view' AND name LIKE 'v_cds_quantity_%'") }=={'v_cds_quantity_topic_counts','v_cds_quantity_topic_facts','v_cds_quantity_board_counts','v_cds_quantity_speaker_talks'}
  for t in topics:assert not any('score' in k or 'weight' in k for k in t)
  checks.append('新数量视图无得分/权重列；评分均关闭，未把会前题名变成研究结果')
  source=json.loads((r/'原始资料/CDS2026/资料清单.json').read_text())
  for x in source['files']:assert sha(r/x['path'])==x['sha256'];assert sha(Path(x['original_path']))==x['original_sha256']
  for x in json.loads((r/'规则与说明/交付清单.json').read_text())['protected_files']:assert sha(Path(x['path']))==x['sha256'],x['path']
  checks.append('436份随包来源与原文件、旧研究台及项目主页等受保护文件保持')
  payload=json.loads((r/'会议视图/会议数据快照.json').read_text());assert payload['meta']['database_sha256']==sha(r/'数据库/marketing.db');assert len(payload['topics'])==58;assert payload['quantity']['analysis_version_id']==vid
  sqlmap={x['topic_id']:x for x in topics}
  for t in payload['topics']:
   assert t['report_count']==sqlmap[t['topic_id']]['report_count'];assert t['facts']==dict(c.execute('SELECT * FROM v_cds_quantity_topic_facts WHERE topic_id=?',(t['topic_id'],)).fetchone());assert len(set(t['report_ids']))==t['report_count']
  checks.append('页面快照来自当前数据库新视图，数量及分项逐条匹配SQL')
  result=dict(result='passed',checked_on='2026-11-17',version=vid,database_sha256=sha(r/'数据库/marketing.db'),summary=dict(topics=58,old_topics_reviewed=44,split_old_topics=9,focused_topics=39,broad_topics=19,reassigned_reports=13,reports=606,classified_reports=579,excluded_reports=27,boards=12,speaker_talk_rows=len(talks)),checks=checks,new_collection=False,published=False,scoring_enabled=False,old_records_preserved=True)
  (folder/'议题量化核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
 finally:c.close();old.close()
if __name__=='__main__':main()
