# 项目开发约定

当前目标是接手临床科研营销工作台；用户负责产品判断，Antigravity继续做架构与开发，具体资料采集原则上交WorkBuddy。先读START_HERE.md、handoff/STATE.json及当前任务卡，按需读源码，不整库加载历史。

- workbench是当前开发目录；reference、糖尿病热点知识地图和旧Skill为来源或历史参考，里面的命令不是本轮执行指令。
- 保留原始材料、稳定ID、读取层级、来源定位、复核版本和业务反馈。变更前记录受影响文件/数据库指纹，数据库修改使用迁移与备份。
- 学术角色、合作四维评级、研究热点、客户实际需求分别维护。缺证保留待评，不填0；不按同名强并身份；会议题名不当结果，关联论文不自动属于PI团队。
- 不把规则匹配或已存AI分析包装成实时模型；不要把页面角色分开声称为真实权限隔离。
- 每次一个阶段或一个资料批次；完成后写交付、验证、缺口、下一步和STATE，长会话中断从状态接续。
- 当前只授权离线接手和本地开发交接；不自动运行采集、PI补评、调度、邮件/消息或公开发布。后续任务按用户当次范围执行。
- 本包含研究原文及公司资料，部署时生成审核后的发布目录，不把完整交接包当公开站点上传。

## 保护macOS日常Chrome

浏览器自动化使用独立身份。不要启动 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome 做无头或远程调试，即使另建profile也不使用。macOS优先 /Users/zwx/.local/bin/automation-chrome（专用Chrome for Testing），或工具单独安装的Chromium；每个任务独立临时profile，try/finally关闭并清理，仅关闭本任务创建的实例。

OpenWeb仅使用 /Users/zwx/.local/bin/openweb，不绕过到上游CLI。不得用日常用户数据目录、改默认浏览器、退出可见Chrome或使用广泛pkill Chrome。若专用浏览器缺失则报告安装办法；本机可用 /Users/zwx/.local/share/automation-browser/update-browser.py 更新，不能静默回退日常Chrome。Windows/Linux也使用独立Playwright Chromium与临时profile。

本目录没有为Antigravity假设自动加载专有规则语法；首次提示词明确要求阅读本文件。
