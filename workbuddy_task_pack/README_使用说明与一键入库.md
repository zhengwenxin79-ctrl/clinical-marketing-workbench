# WorkBuddy 采集交付包使用说明（零终端与自动化入库指南）

本交付包专为 **WorkBuddy**（智能体/采集机器人）量身定制，现已支持**完全免人工敲命令（零终端）**与 **GitHub Actions 全自动云端发布**。

---

## 📁 交付包内容清单

1. **`01_给WorkBuddy的执行提示词.txt`**：全套提示词，直接全选复制给 WorkBuddy。
2. **`02_首批监控锚点清单_Top15.json`**：精选出的 15 个顶级医学会与国际重大会议清单及官网入口。
3. **`03_交付规范与数据契约_Schema.json`**：严格的 JSON 结构契约。
4. **`04_标准交付示例_batch_sample.json`**：标准产物样本（Few-Shot 参照）。
5. **`05_WorkBuddy下周会议采集与ABCD评级提示词.txt`**：下周会议专属采集评级指令。
6. **`06_官方评级金标准参考_20261123周度.csv`**：评级标杆参考对照表。

---

## 🚀 两种免终端（Zero-Terminal）入库方式

### 方式一：网页端一键选择文件导入（最快最简单，完全不用命令行）
无论 WorkBuddy 把采集结果存放在何处（或直接在聊天中发给您），您只需：
1. 打开在线审核工作台：[https://zhengwenxin79-ctrl.github.io/clinical-marketing-workbench/会议审核入库.html](https://zhengwenxin79-ctrl.github.io/clinical-marketing-workbench/会议审核入库.html)
2. 在工具栏上点击 **【📁 导入交付文件 (JSON/CSV)】**；
3. 选择 WorkBuddy 生成的 `.json` 或 `.csv` 文件；
4. **网页即刻自动解析全部会议、自动标记 ABCD 评级与重点标签，直接加载进待审核列表！**

---

### 方式二：WorkBuddy 直推 GitHub，云端自动入库发布（全自动无人值守）
如果 WorkBuddy 拥有终端权限，您只需在给 WorkBuddy 的提示词最后加一段指令：
> “采集生成 JSON 文件后，保存至 `crawled_batches/` 目录，然后执行以下 Git 命令推送至 GitHub：
> ```bash
> git add crawled_batches/
> git commit -m "feat(batch): WorkBuddy 采集批次交付"
> git push origin main
> ```”

**云端自动化流（已配置 GitHub Actions CI/CD）：**
1. GitHub 检测到 WorkBuddy 推送了新的采集文件；
2. 云端 Linux 容器自动运行 `python tools/auto_ingest_batches.py` 自动入库与去重；
3. 自动重新生成静态工作台并发布到 GitHub Pages；
4. 您无需在本地电脑运行任何命令，直接在手机或电脑浏览器打开页面即可审核！
