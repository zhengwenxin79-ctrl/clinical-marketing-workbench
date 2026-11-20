# Windows迁移：从这里开始

这个包包含两部分：`workbench`是完整的可运行工作台副本，`skill`是Windows适配版WorkBuddy技能。不要只传Skill ZIP；GitHub目前只存展示网页，不能替代本地采集项目。

## 三步使用

1. 把整个迁移ZIP传到Windows电脑，右键“全部解压”，建议放在普通本地目录，例如 `D:\clinical-research-windows` 或 `C:\Users\你的用户名\Documents\clinical-research-windows`。文件夹名可以更改，避免放在系统保护目录或多人同步运行的网盘目录。
2. 安装WorkBuddy及Python 3.9以上。安装Python时启用命令行入口；在终端确认 `py -3 --version`（或 `python --version`）能返回版本，`curl.exe --version`能运行。项目无需额外pip依赖。
3. 在WorkBuddy上传 `skill\diabetes-conference-monitor-windows.zip`，选择“糖尿病会议采集与复核（Windows版）”；工作空间选择 `workbench` 文件夹。先发送下面的“仅检查环境”提示词，通过后再执行单次采集。

也可以双击包根目录的 `check-environment.cmd`：它只检查环境，不联网抓会议、不生成新草稿、不设置任务。找不到Python或curl.exe时，先解决环境缺项，再回WorkBuddy运行。

## 可以直接复制给WorkBuddy

### 首次：只检查

```text
使用“糖尿病会议采集与复核（Windows版）”技能。
工作空间是我刚选择的workbench文件夹，请使用实际目录。
先读取SKILL.md，定位已安装技能的scripts/run.py，用py -3 -X utf8（若无py则用已确认版本的python -X utf8）执行--mode check，--project-root传入workbench完整路径。
本次只检查环境，不联网采集、不修改项目、不设置定时任务、不发布GitHub。
根据脚本输出告诉我是否就绪和缺少什么。
```

### 检查通过后：采集一次

```text
使用“糖尿病会议采集与复核（Windows版）”技能。
在当前workbench空间先执行环境检查，通过后调用固定入口--mode collect采集一次。
保持8个来源及解析代码原样，只生成待复核版本；不要恢复定时任务，不调用正式应用或GitHub发布。
依据真实日志汇报运行编号、完整/部分/失败、成功来源数/总数、新候选数、失败或待核来源以及网页和报告的位置。
```

完整提示词位于 `skill\diabetes-conference-monitor-windows\references\任务提示词.md`。

## 在哪里查看

- 当前正式网页：`workbench\index.html`，与已发布版本一致。
- 最近的待复核网页：`workbench\monitoring\待复核\index.html`。采集后刷新页面，点击“本周新增／更新”。
- 运行记录：`workbench\monitoring\runs\运行ID`；最近已有观察已一并带上，便于后续去重。
- 仅验收已有运行可用 `--mode verify --run-id 编号`，不会再次抓取。

本包不含Git仓库、GitHub令牌或发布权限。Windows上产出的草稿先留在本机复核；“确认后发布”功能仍待后续接入，原线上网页不会因此改变。

## 离线回放与锁

回放已有快照可用 `--mode replay --run-id 已有编号`，不联网但会生成新草稿并更新本机最新入口，检查时间保持原时间。除非你要求验证回放，否则首次只运行check。

每次采集使用 `workbench\monitoring\.collector.lock.d` 防止同一项目重叠运行。正常退出自动清理。若强制结束或断电后留下锁，先确认采集进程都已退出，再删除这个锁文件夹；不要在另一次采集仍运行时删除。

## 适配与验证范围

Windows版采用目录锁、显式UTF-8、列表参数调用curl.exe及北京时间UTC+8，避免依赖POSIX的fcntl和额外时区数据库。Python使用你电脑的实际解释器路径启动子进程，不依赖Mac路径。

打包时只做已有快照的离线验证，没有重新联网采集，没有创建定时任务。当前环境是macOS，尚未在Windows实机及其WorkBuddy客户端运行；首次check和一次单次采集用于核对实际Python、curl、网络及权限。发生错误时保留原输出，不让模型改写采集规则绕过检查。

官方参考：[WorkBuddy工作空间](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Task-Bar)、[Python文本I/O](https://docs.python.org/3/library/io.html)、[Python时区数据依赖](https://docs.python.org/3/library/zoneinfo.html)。
