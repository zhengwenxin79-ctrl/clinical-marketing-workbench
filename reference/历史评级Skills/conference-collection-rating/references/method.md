# 执行与台账规范

## 1. 漏会检查的分母

先有本轮必须检查的来源任务，再有找到的候选。默认检查：两大组织分别覆盖六领域、每领域其他全国专题组织、八个覆盖省市的医学会与医师协会、三组会务渠道、每领域开放检索，以及上轮储备、核心系列和历史漏项。医学会与医师协会不可相互替代；泛血管交叉方向也不假设一定存在同名分会。

同一领域的子方向要查到。例如神经精神至少分别看神经内科、精神医学、痴呆与认知障碍；不得只查一次“神经精神会议”就宣布该领域完成。覆盖省份用于寻找入口，销售覆盖仍按明确的城市，不扩大到全省。

组织名称检索至少有一条不限制主站域名的路径，才能发现委托会务站和承办医院公告。关键词组合使用同义词和OR，不把年会、医师大会、征文、具体周日期同时设为必含词。无年份查询用于发现系列和旧届线索，旧届信息不能直接成为本届事实。

台账任务中：

- `status`：`pending` 未开始、`partial` 部分检查、`blocked` 受限、`complete` 已完成所声明范围。
- `attempts`：每次实际访问或检索的 `url` 或 `query`、`checked_at`、`result`。不得按计划生成伪日志。
- `checked_topics`：本任务实际查过的子方向；`extent_complete` 表示相关列表/章节范围已读完，不能根据页面标题猜测。
- `candidate_ids`：该任务发现的候选编号；零结果可以填空，但应有实际查询及范围记录。
- `gap_action`：失败入口、未读页面、需要截图或人工辅助的下一步。
- `documents`：PDF的 `page_count`、`processed_pages`、`image_pages`、`ocr_pages`；无关页可以在 `excluded_pages` 中逐页解释。网页只返回空壳时，不能勾选范围完成。
- `enumerations`：读取计划表或目录时登记 `url, total_items, items`。`total_items` 是实际目录或所声明完整范围内的条目数，不使用搜索引擎估算命中数。每个item含 `source_item_id, title, kind`；`kind=conference` 要连 `candidate_id`，其他条目写 `reason`。目录有10条却只记入选的3条，会被检查为缺口。

首次建立组织与系列底表需要完整扫年度计划和当年目录；后续可复用有来源的底表，逐项检查增量、未知日期、近期变更及新系列，不必每周重复下载全部历史文件。未核实的年度计划月份不能作为排除当期候选的唯一依据。

## 2. 证据按发布者、字段和有效版本判断

不把整个网站永久分成A/B/C后直接采信。聚合平台上的主办方原文、医院自己的参会报道与普通转载，身份不同。确认主办委托关系后，会务微站可承载正式通知；站点名称本身不构成授权证明。

| 证据角色 `role` | 适用范围 |
|---|---|
| `organizer_notice` | 主办方正式通知或更正，核本届日期、城市及身份 |
| `official_conference_site` | 经主办关系核实的大会官网，以本届内容为准 |
| `authorized_platform_notice` | 经核实受委托发布的正式会务通知，保留发布者和主办关系 |
| `annual_plan` | 发现全年会议、组织身份和计划安排，不确认最终举办日期 |
| `procurement_notice` | 筹备、拟定安排及变化线索，不等于最终举办通知 |
| `cme_plan` | 继教立项或申报计划，不等于实际会期或会议级别 |
| `exhibitor_schedule` / `funding_notice` / `venue_schedule` | 辅助追查，不能单独作为最终会期 |
| `hospital_report` | 核实其明确披露的参会或举办事实，不外推未写出的完整会期 |
| `aggregator` / `search_snippet` | 发现及定位原文；未读到原文不能冒充正式通知核实 |

最终日期通常追到前三种角色，其他材料不足时保留计划/待核实。旧正式通知不能因为域名权威就压过新的有效更正；无法判定哪份有效时保留冲突。不把“新发布的转载”误当“新的主办方安排”。

每条证据记录：`id, url, publisher, role, origin_id, published_at, accessed_at, edition_year, claims`，针对单场会议的事实另记 `candidate_id`。日期用ISO格式；发布日期未知可为null，须在备注说明。`origin_id` 表示原始公告身份，不同网址转载同一通知仍同源。`claims` 仅写原文明示的字段，例如 `main_start, main_end, city, formal_national_annual`。补一句简短原文或页码便于复核，避免复制全文。

`status` 可记 `active/superseded/withdrawn`，旧通知被替代后仍保留。只比较同届、同字段的证据。回溯时设 `meta.as_of`，不可借截止日之后才发布的事实假装当时已知。

## 3. 候选、储备与人工意见

每条候选最少包含：

```json
{
  "id": "自定稳定编号",
  "name": "本届会议名称",
  "edition_year": 2026,
  "series_id": null,
  "domains": ["neuropsych"],
  "format": "onsite",
  "city": null,
  "main_start": null,
  "main_end": null,
  "date_status": "unknown",
  "date_evidence_ids": [],
  "identity_evidence_ids": [],
  "formal_national_annual": false,
  "business_fit": "unclear",
  "operational_only": false,
  "priority": "待确认",
  "reason": "说明根据与待补信息",
  "disposition": "weekly_pending",
  "disposition_reason": "安排待核实",
  "discovery_task_ids": [],
  "manual_review": null
}
```

`date_status`：`confirmed/planned/conflict/unknown/cancelled`。`business_fit`：`relevant/mixed_relevant/unclear/low`。`disposition`：`weekly_confirmed/weekly_pending/reserve/excluded/duplicate`。重复项另填 `duplicate_of`，不删除发现记录。

完整目录中的范围外会议也可只建最小候选：`domains=[]`、`disposition=excluded`并说明超出本轮领域。领域尚不清楚时允许空数组、关注等级待确认；不要为了过检查而硬归入六大类。`nonconference`仅用于确实不是会议的新闻/通知，不用于藏掉低相关会议。

与来源任务的 `candidate_ids` 双向关联。分类不依赖完整PI表；`formal_national_annual=true` 要有组织或正式大会资料支持其身份，不用标题猜。领域宽泛但未发现低相关证据的正式核心年会，先重点追踪并补查；已有明确低相关证据则说明例外理由，不机械抬高。

发现来源可记在 `discovery_evidence_ids`；明确低相关或纯操作判断用 `content_evidence_ids` 连接内容依据。若写“已结束”，用 `occurrence_evidence_ids` 连接明确披露实际举办事实的材料，`claims.held=true`，不只依据日期已过。

主会、附属活动分别记时间，附属活动写入可选 `sessions`；证据只给总日程时不自行猜主会是哪天。大会在境内举办即属于国内范围，不按名字中的“国际”误排除。

`series_checks` 对registry里的核心系列逐一记录本届状态：`linked` 连到候选；`not_found` 本轮尚未找到并说明查过的路径；`pending` 尚未查。`candidate_ids` 可连到本周、储备或已取消项；系列存在不意味着每年一定举办。不沿用上届日期或人数推算本届。

使用上轮台账时，保留人工 `manual_review` 原文，不把它当本轮最新事实。对上轮推荐与新证据有冲突的记录提示复核，不自动改写已确认意见。

## 4. 查漏与停止条件

每场已知重点会议都要得到“本周/其他日期/安排待核实/未找到/取消”的去向。不能只抽查已经推荐的会议。开放检索用于发现未登记组织和新会议品牌；用户补充漏会后，更新对应组织、领域和系列，而不只追加一个名字。

可交付本轮结果的前提是：任务执行范围有记录、候选有去向、核心系列有交代、来源冲突有说明。访问失败不阻止先交有依据的部分，但必须将覆盖结论标为部分覆盖，并列人工辅助或下一次补查事项。不能用“连搜几次没新会”替代组织与系列检查。

检查命令：

```bash
python3 scripts/conference_run.py audit run.json --output audit.json
```

退出码0：台账无规则错误、预定覆盖任务有记录且未留核心系列缺口，可供人工审核；1：结构、日期、关联或评级存在错误；2：无此类错误但覆盖仍有缺口。任何返回值都不证明实际查询日志真实或互联网会议全集已覆盖。

比较旧版时，使用相同目标周、截止日和业务范围。独立核对集由mentor、已知漏会和组织计划提供，需逐场核最新去向。分别记录发现遗漏、误筛、日期错误；“新结果比旧表多”不足以证明找全。种子核心会议参与调试后属于回归用例，下一轮另留未参与调试的会议验证泛化。
