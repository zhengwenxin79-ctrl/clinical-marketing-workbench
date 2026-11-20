#!/bin/zsh
set -eu
TASK_CENTER="${0:A:h}"
if ! command -v python3 >/dev/null 2>&1; then
  print '请先安装Python 3.9或以上版本，再重新打开这个启动文件。'
  read '?按回车关闭'
  exit 1
fi
exec python3 "$TASK_CENTER/脚本/启动维护台.py"
