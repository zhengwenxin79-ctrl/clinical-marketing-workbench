"""Export & Stage Static Pages for GitHub Pages Deployment.
Packages:
1. Primary clinical workbench (workbench/领域工作台/index.html and dist/index.html)
2. Unified portal (打开工作台.html)
3. Role login portal (登录工作台.html)
4. Conference review interface (会议审核入库.html)
5. Full static subviews:
   - workbench/会议视图/ (ada.html, index.html for CDS)
   - workbench/会议总入口/
   - workbench/标志物视图/
   - workbench/论文视图/
   - workbench/规则与说明/
   - workbench/原始资料/
   - workbench/框架配置/
"""
from pathlib import Path
import shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
WORKBENCH = ROOT / "workbench"

def copy_folder_clean(src: Path, dst: Path):
    if not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        # skip git, node_modules, temp or pycache
        if item.name.startswith(".") or item.name in ("__pycache__", "node_modules"):
            continue
        dest_item = dst / item.name
        if item.is_dir():
            shutil.copytree(item, dest_item, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest_item)

def export_all():
    print("=== [Export Pages] Staging Static Assets for GitHub Pages ===")
    DIST.mkdir(parents=True, exist_ok=True)

    # 1. Rebuild fresh workbench
    build_script = ROOT / "workbench/脚本/生成领域工作台.py"
    if build_script.is_file():
        subprocess.check_call([sys.executable, "-X", "utf8", str(build_script)])
        print("  -> Rebuilt domain workbench via 生成领域工作台.py.")

    # 2. Copy workbench/领域工作台
    domain_wb = WORKBENCH / "领域工作台"
    dist_domain_wb = DIST / "workbench/领域工作台"
    copy_folder_clean(domain_wb, dist_domain_wb)
    print("  -> Staged workbench/领域工作台/ (index.html, src, etc.).")

    # 3. Create root index.html:
    # Provides seamless transparent redirect to workbench/领域工作台/index.html preserving query & hash,
    # and falls back to a clean embedded workbench for no-js.
    workbench_index = domain_wb / "index.html"
    if workbench_index.is_file():
        # Copy to root index
        root_index = DIST / "index.html"
        content = workbench_index.read_text(encoding="utf-8")
        # Prepend fast auto-redirect script to head for seamless path alignment
        redirect_script = """<script>
// Fast seamless redirect to canonical path preserving hash and search params
(function(){
  var p = location.pathname;
  if (!p.includes('workbench/领域工作台')) {
    var target = 'workbench/领域工作台/index.html' + location.search + location.hash;
    location.replace(target);
  }
})();
</script>"""
        if "<head>" in content:
            content = content.replace("<head>", "<head>\n  " + redirect_script, 1)
        root_index.write_text(content, encoding="utf-8")
        print("  -> Configured root dist/index.html with auto-redirect to workbench/领域工作台/.")

    # 4. Copy other portal pages to dist/
    for page_name in ["打开工作台.html", "登录工作台.html"]:
        src = ROOT / page_name
        if src.is_file():
            shutil.copy2(src, DIST / page_name)
            print(f"  -> Copied {page_name} to dist/.")

    # 5. Copy conference review page
    review_html = domain_wb / "会议审核入库.html"
    if review_html.is_file():
        shutil.copy2(review_html, DIST / "会议审核入库.html")
        (DIST / "workbench/领域工作台").mkdir(parents=True, exist_ok=True)
        shutil.copy2(review_html, DIST / "workbench/领域工作台/会议审核入库.html")
        print("  -> Copied 会议审核入库.html to dist/ and dist/workbench/领域工作台/.")

    # 6. Copy full view suites to BOTH dist/workbench/ and dist/ root to guarantee zero 404s
    view_folders = [
        "会议视图",
        "会议总入口",
        "标志物视图",
        "论文视图",
        "规则与说明",
        "原始资料",
        "框架配置"
    ]
    for folder in view_folders:
        src_folder = WORKBENCH / folder
        if src_folder.is_dir():
            # Copy to dist/workbench/<folder> (canonical path for ../<folder> from 领域工作台)
            copy_folder_clean(src_folder, DIST / "workbench" / folder)
            # Also copy to dist/<folder> (fallback path if opened from root)
            copy_folder_clean(src_folder, DIST / folder)
            print(f"  -> Staged view suite: workbench/{folder}/ (to dist/workbench/ & dist/).")

    print(f"=== [Export Pages Complete] Output directory: {DIST} ===")
    return DIST

if __name__ == "__main__":
    export_all()
