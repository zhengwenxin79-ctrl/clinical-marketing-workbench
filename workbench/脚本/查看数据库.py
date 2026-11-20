"""只读查看已建SQL视图；不修改数据库。"""
from pathlib import Path
import argparse,json,sqlite3
VIEWS=['v_conference_inventory','v_report_detail','v_topic_counts','v_board_counts','v_leader_talks','v_biomarker_title_scope','v_speaker_tiers','v_speaker_tier_counts','v_conference_tiers','v_tier_speaker_talks','v_cds_quantity_topic_counts','v_cds_quantity_board_counts','v_cds_quantity_topic_facts','v_cds_quantity_speaker_talks','v_ada_quantity_topic_counts','v_ada_quantity_board_counts','v_ada_quantity_topic_facts','v_ada_quantity_speaker_talks']
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--view',choices=VIEWS,default=VIEWS[0]);ap.add_argument('--limit',type=int,default=20);a=ap.parse_args();c=sqlite3.connect((a.root.resolve()/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
try:
 c.execute('PRAGMA query_only=ON');rows=c.execute('SELECT * FROM '+a.view+' LIMIT ?',(max(1,min(a.limit,2000)),)).fetchall();print(json.dumps([dict(r) for r in rows],ensure_ascii=False,indent=2))
finally:c.close()
