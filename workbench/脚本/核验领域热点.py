"""核对领域热点导出与SQLite主议题、去重报告和讲者关联。只读。"""
from pathlib import Path
import sqlite3,json,hashlib
ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'会议总入口'
    data=json.loads((out/'领域热点数据快照.json').read_text())
    c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True)
    c.row_factory=sqlite3.Row
    assert len(data['reports'])==len({r['report_id'] for r in data['reports']})
    assert len(data['topics'])==58 and len(data['boards'])==12
    expected={}
    for conf in data['conferences']:
        cid=conf['conference_id']
        versions=c.execute("SELECT analysis_version_id FROM analysis_versions WHERE conference_id=? AND is_current_snapshot=1 AND analysis_kind IN ('topic_quantity','ada_topic_quantity')",(cid,)).fetchall()
        assert len(versions)==1
        vid=versions[0][0]
        expected[cid]={}
        for cohort,condition in [('talks',"r.report_format IN ('大会报告','专题报告','论文发言')"),('posters',"r.report_format IN ('海报报告','晚期突破海报')"),('all','1=1')]:
            rows=c.execute(f'''SELECT r.report_id,rc.primary_topic_id FROM reports r JOIN report_classifications rc USING(report_id)
                WHERE r.conference_id=? AND rc.analysis_version_id=? AND rc.eligible=1 AND {condition}''',(cid,vid)).fetchall()
            ids={r['report_id'] for r in rows}
            actual={r['report_id'] for r in data['reports'] if r['conference_id']==cid and (cohort=='all' or r['cohort']==cohort)}
            assert ids==actual,(cid,cohort)
            assert len(ids)==conf['cohorts'][cohort]['classified']
            counts={}
            for row in rows:
                tid=row['primary_topic_id']
                if cid!='CDS2026':
                    tid=c.execute('SELECT template_topic_id FROM conference_topic_scope WHERE topic_id=?',(tid,)).fetchone()[0]
                counts[tid]=counts.get(tid,0)+1
            expected[cid][cohort]=dict(denominator=len(ids),counts=counts)
    people={p['key']:p for p in data['people']}
    for r in data['reports']:
        for key in r['speaker_keys']:
            p=people[key]
            assert p['conference_id']==r['conference_id']
            sql='''SELECT COUNT(*) FROM agenda_participants ap JOIN reports r USING(agenda_item_id)
                WHERE r.report_id=? AND ap.person_id=? AND ap.agenda_role='speaker' ''' if r['conference_id']=='CDS2026' else '''SELECT COUNT(*) FROM agenda_participants ap JOIN conference_program_occurrences o USING(agenda_item_id)
                WHERE o.report_id=? AND ap.person_id=? AND ap.agenda_role='speaker' '''
            assert c.execute(sql,(r['report_id'],p['person_id'])).fetchone()[0]>0
    c.close()
    backup=Path((out/'本轮备份位置.txt').read_text().strip())
    protected=json.loads((backup/'受保护文件指纹.json').read_text())
    changed=[p for p,h in protected.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    assert not changed,changed
    assert hashlib.sha256((ROOT/'数据库/marketing.db').read_bytes()).hexdigest()==data['meta']['database_sha256']
    result=dict(result='passed',topic_count=len(data['topics']),board_count=len(data['boards']),
        report_count=len(data['reports']),expected=expected,protected_files_unchanged=len(protected),
        database_unchanged=True,new_collection=False,published=False)
    (out/'领域热点数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='expected'},ensure_ascii=False))

if __name__=='__main__':main()
