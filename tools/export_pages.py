"""Export & Stage Static Pages for GitHub Pages Deployment.
Packages:
1. Primary clinical workbench (index.html)
2. Unified portal (打开工作台.html)
3. Role login portal (登录工作台.html)
4. Conference review interface (会议审核入库.html)
5. Configuration and static assets
"""
from pathlib import Path
import shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

def export_all():
    print("=== [Export Pages] Staging Static Assets for GitHub Pages ===")
    DIST.mkdir(parents=True, exist_ok=True)

    # 1. Rebuild fresh workbench
    build_script = ROOT / "workbench/脚本/生成领域工作台.py"
    if build_script.is_file():
        subprocess.check_call([sys.executable, "-X", "utf8", str(build_script)])
        print("  -> Rebuilt domain workbench via 生成领域工作台.py.")

    # 2. Copy workbench index.html as root index.html
    workbench_html = ROOT / "workbench/领域工作台/index.html"
    if workbench_html.is_file():
        shutil.copy2(workbench_html, DIST / "index.html")
        (DIST / "workbench/领域工作台").mkdir(parents=True, exist_ok=True)
        shutil.copy2(workbench_html, DIST / "workbench/领域工作台/index.html")
        print("  -> Copied workbench/领域工作台/index.html to dist/index.html.")

    # 3. Copy other portal pages
    for page_name in ["打开工作台.html", "登录工作台.html"]:
        src = ROOT / page_name
        if src.is_file():
            shutil.copy2(src, DIST / page_name)
            print(f"  -> Copied {page_name} to dist/.")

    # 4. Copy conference review page
    review_html = ROOT / "workbench/领域工作台/会议审核入库.html"
    if review_html.is_file():
        shutil.copy2(review_html, DIST / "会议审核入库.html")
        shutil.copy2(review_html, DIST / "workbench/领域工作台/会议审核入库.html")
        print("  -> Copied 会议审核入库.html to dist/.")

    # 5. Copy static assets / configurations if needed
    config_src = ROOT / "workbench/框架配置"
    if config_src.is_dir():
        dist_config = DIST / "workbench/框架配置"
        dist_config.mkdir(parents=True, exist_ok=True)
        for f in config_src.glob("*.json"):
            shutil.copy2(f, dist_config / f.name)
        print("  -> Copied framework JSON configurations to dist/.")

    print(f"=== [Export Pages Complete] Output directory: {DIST} ===")
    return DIST

if __name__ == "__main__":
    export_all()
