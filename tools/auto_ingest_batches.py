# -*- coding: utf-8 -*-
"""Auto-ingest batch files in crawled_batches/ directory.
Executed during GitHub Actions CI or local automated pipelines.
"""
from pathlib import Path
import json, csv, os, sys, sqlite3, datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import manage_conference_updates

BATCHES_DIR = ROOT / "crawled_batches"
CONFIG_QUEUE = ROOT / "workbench/框架配置/static_demo_queue.json"

def auto_ingest_all():
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    json_files = sorted(BATCHES_DIR.glob("*.json"))
    csv_files = sorted(BATCHES_DIR.glob("*.csv"))
    
    print(f"=== [Auto-Ingest Batches] Found {len(json_files)} JSON and {len(csv_files)} CSV in {BATCHES_DIR} ===")
    
    ingested_count = 0
    all_items = []
    
    # 1. Ingest JSON files
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", data) if isinstance(data, dict) else data
            batch_id = data.get("batch_id", jf.stem) if isinstance(data, dict) else jf.stem
            if isinstance(items, list) and items:
                res = manage_conference_updates.ingest_crawled_conferences(items, batch_id=batch_id)
                print(f"  -> Ingested {jf.name}: {res.get('total')} items ({res.get('first_seen')} first seen)")
                ingested_count += len(items)
                for it in items:
                    it["batch_id"] = batch_id
                    all_items.append(it)
        except Exception as e:
            print(f"  -> Error ingesting {jf.name}: {e}")

    # 2. Sync full pending queue to static_demo_queue.json for GitHub Pages
    try:
        conn = manage_conference_updates.get_db()
        c = conn.cursor()
        rows = [dict(r) for r in c.execute("SELECT * FROM conference_review_queue ORDER BY created_at DESC").fetchall()]
        conn.close()
        
        if rows:
            print(f"  -> Exporting {len(rows)} queue items to {CONFIG_QUEUE.name} for GitHub Pages static sync...")
            with open(CONFIG_QUEUE, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
            
            # Update 会议审核入库.html static queue
            review_html = ROOT / "workbench/领域工作台/会议审核入库.html"
            if review_html.is_file():
                content = review_html.read_text(encoding="utf-8")
                import re
                pat = r"const STATIC_DEMO_QUEUE = \[.*?\];"
                rep = f"const STATIC_DEMO_QUEUE = {json.dumps(rows, ensure_ascii=False, indent=2)};"
                new_c = re.sub(pat, rep, content, flags=re.DOTALL)
                review_html.write_text(new_c, encoding="utf-8")
                print("  -> Updated STATIC_DEMO_QUEUE in 会议审核入库.html")
    except Exception as e:
        print(f"  -> Error syncing to static queue: {e}")

    print(f"=== [Auto-Ingest Complete] Total {ingested_count} items processed. ===")

if __name__ == "__main__":
    auto_ingest_all()
