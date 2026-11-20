# WorkBuddy 采集交付包使用说明与一键入库指南

本交付包专为 **WorkBuddy**（智能体/爬虫）量身定制，用于标准化执行 2026 年临床学术会议动态采集任务，并与主系统无缝接轨。

---

## 📁 交付包内容清单

1. **`01_给WorkBuddy的执行提示词.txt`**：全套提示词，包含角色设定、采集范围、提取字段、纪律规则及输出格式，直接全选复制给 WorkBuddy。
2. **`02_首批监控锚点清单_Top15.json`**：精选出的 15 个顶级医学会与国际重大会议清单及官网入口。
3. **`03_交付规范与数据契约_Schema.json`**：严格的 JSON 结构契约。
4. **`04_标准交付示例_batch_sample.json`**：标准产物样本，可供 WorkBuddy 作为 Few-Shot 参照。

---

## 🚀 执行四步走

### 第一步：将提示词给到 WorkBuddy
打开 WorkBuddy 界面，全选复制 **`01_给WorkBuddy的执行提示词.txt`** 发送给它开始执行。

### 第二步：保存产物文件
让 WorkBuddy 将采集生成的 JSON 结果保存到项目目录下的：
```
clinical-marketing-antigravity-20261119/crawled_batches/batch_20261120_workbuddy.json
```
*(注：如果目录 `crawled_batches/` 尚未存在，工具会自动创建)*

### 第三步：一键校验并入库暂存队列（命令行）
在项目根目录下打开终端，执行以下命令：
```bash
python tools/manage_conference_updates.py --import-file crawled_batches/batch_20261120_workbuddy.json
```
**系统将自动完成：**
1. 校验 JSON 格式与字段合法性；
2. 自动与现有数据库比对（首次收录 `first_seen` / 日程变更 `source_update` / 重复日程 `duplicate`）；
3. 将重复项自动过滤归档，有效新会议或日程变更自动存入 `conference_updates.db` 的【待市场部审核队列】。

### 第四步：市场部审核发布
打开已统一风格的审核工作台：
- 本地访问：[http://127.0.0.1:8768/workbench/领域工作台/会议审核入库.html](http://127.0.0.1:8768/workbench/领域工作台/会议审核入库.html)
- 或线上访问：[https://zhengwenxin79-ctrl.github.io/clinical-marketing-workbench/会议审核入库.html](https://zhengwenxin79-ctrl.github.io/clinical-marketing-workbench/会议审核入库.html)

在界面上点击 **【✅ 批准并发布】**，数据即刻生效并同步至首页的每周最新动态！
