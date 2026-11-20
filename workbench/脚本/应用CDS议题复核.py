"""事务追加新议题分类版本与复核记录，保留旧版和原始数据。"""
from pathlib import Path
import json,hashlib,sqlite3
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 root=ROOT;folder=root/'规则与说明/CDS议题数量复核_2026-11-17';plan_path=folder/'议题复核方案.json';rules=folder/'数量榜口径.md';plan=json.loads(plan_path.read_text());baseline=json.loads((folder/'变更前基线.json').read_text());version=plan['version'];db=root/'数据库/marketing.db';c=sqlite3.connect(db);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:
  if c.execute("SELECT 1 FROM sqlite_schema WHERE name='quantity_rule_versions'").fetchone():
   old=c.execute('SELECT * FROM quantity_rule_versions WHERE analysis_version_id=?',(version,)).fetchone()
   if old:
    assert old['rules_sha256']==sha(rules) and old['decisions_sha256']==sha(plan_path),'同版本规则/方案已改变；停止，需新版本'
    print(json.dumps({'result':'already_applied','version':version},ensure_ascii=False));return
  assert sha(db)==baseline['database_sha256'],'数据库已变化，停止等待核对'
  c.executescript('BEGIN IMMEDIATE;\n'+(root/'规则与说明/003_CDS议题数量复核.sql').read_text())
  def ins(table,**v):c.execute(f"INSERT INTO {table} ({','.join(v)}) VALUES ({','.join('?' for _ in v)})",list(v.values()))
  source=c.execute('SELECT * FROM analysis_versions WHERE analysis_version_id=?',(plan['source_version'],)).fetchone()
  ins('analysis_versions',analysis_version_id=version,conference_id='CDS2026',analysis_kind='topic_quantity',rule_label='宽度复核后58议题数量榜',review_status='ai_title_review_pending_mentor',is_current_snapshot=1,scoring_enabled=0,material_id=source['material_id'],method_note='原材料字段引用旧定义作为前版参考；本版定义、逐题决策与缺口见规则与说明/CDS议题数量复核_2026-11-17/议题复核方案.json。只按数量排序，分项不加权。')
  ins('quantity_rule_versions',analysis_version_id=version,previous_analysis_version_id=plan['source_version'],reviewed_on='2026-11-17',rules_path=str(rules.relative_to(root)),rules_sha256=sha(rules),decisions_path=str(plan_path.relative_to(root)),decisions_sha256=sha(plan_path),review_method=plan['review_method'],denominator=579,new_collection=0,scoring_enabled=0)
  for t in plan['topics']:
   ins('research_topics',topic_id='CDS2026:'+t['code'],conference_id='CDS2026',legacy_topic_id=t['code'],parent_topic_id=t['parent_id'],node_type='topic',name=t['name'],research_question=t['question'],taxonomy_status='working_classification',material_id=source['material_id'])
  for rv in plan['scope_reviews']:
   ins('topic_scope_reviews',analysis_version_id=version,old_topic_id=rv['old_topic_id'],old_report_count=rv['old_report_count'],action=rv['action'],rationale=rv['reason'],evidence_gaps=rv['gaps'])
  for t in plan['topics']:
   ins('topic_scope_review_targets',analysis_version_id=version,old_topic_id='CDS2026:'+t['origin'],new_topic_id='CDS2026:'+t['code'],width_status=t['width_status'],boundary_text=t['boundary'],evidence_gaps=t['gaps'])
  for r in plan['report_decisions']:
   ins('report_classifications',report_id=r['report_id'],analysis_version_id=version,primary_topic_id='CDS2026:'+r['new_code'] if r['new_code'] else None,scope_original=r['scope_original'],eligible=r['eligible'],classification_basis='AI题名复核：'+r['basis'],material_id=r['source_material_id'],source_locator=r['source_locator'])
   ins('report_topic_review_notes',analysis_version_id=version,report_id=r['report_id'],previous_topic_id=r['old_topic_id'],decision_code=r['decision'],rationale=r['basis'],evidence_gaps=r['gaps'],source_material_id=r['source_material_id'],source_locator=r['source_locator'])
  assert c.execute('SELECT COUNT(*) FROM v_cds_quantity_topic_counts').fetchone()[0]==58;assert c.execute('SELECT SUM(report_count) FROM v_cds_quantity_topic_counts').fetchone()[0]==579
  assert c.execute('SELECT COUNT(*) FROM v_topic_counts').fetchone()[0]==44;assert c.execute('SELECT SUM(report_count) FROM v_topic_counts').fetchone()[0]==579
  assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';c.commit()
  print(json.dumps(dict(result='applied',version=version,topics=58,denominator=579,old_topics_preserved=44,new_collection=False,published=False,database_sha256=sha(db)),ensure_ascii=False))
 except BaseException:c.rollback();raise
 finally:c.close()
if __name__=='__main__':main()
