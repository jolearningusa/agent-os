# L02a 采集探针运行时准备

本切片为 L02 的独立运行环境准备步骤，依据 [L0a ADR](../adr/0001-hermes-local-lab.zh-CN.md)。
用户于 2026-11-16 明确授权下载独立 Python 3.14、uv 和固定 Hermes 提交的锁定核心依赖。
范围不含 Ollama、模型权重或语音 extras，不修改系统 Python。

## 固定输入与边界

- 目标平台：macOS 14.4.1、arm64；本次机器 Apple M2、8 GiB。其他平台重新审核清单。
- [运行时清单](../../configs/probe-runtime-macos-arm64.json)：uv 0.13.8 的 macOS arm64
  wheel、Python 3.14.10（python-build-standalone 20261110）的精确 URL/SHA-256，
  以及此次审核的 66 个核心包版本。Python 由固定 uv 的内置元数据校验下载哈希。
- uv wheel 哈希来自 [PyPI 版本元数据](https://pypi.org/pypi/uv/0.13.8/json)；Python
  哈希核对 [该 uv 版本的下载元数据](https://github.com/astral-sh/uv/blob/0.13.8/crates/uv-python-managed/download-metadata.json)。
- 源码使用 [harness.lock.json](../../harness.lock.json) 的 fork/commit 和六个文件哈希。
  不初始化其他 submodule。此处没有 fork 补丁，不安装 Node/UI 或语音依赖。

所有下载物位于被 Git 忽略的 `.local/harness-lab/probe/`；bootstrap、managed Python、
缓存、源码和依赖 venv 分开存放。私有根目录为 0700、安装日志为 0600；源码与依赖
保留发行文件权限。写私有数据的每个进程设 umask 0077，不依赖前次工具调用。
安装有联网权限，探针执行时的出站与文件隔离在 L02b 单独验证；这里没有启动
Hermes，也不能证明 Agent 的可行性或隔离。

核心同步使用 frozen、no-dev、no-default-groups、no-install-project、no-build。
不安装 Hermes 本身，后续探针通过源码路径导入；避免未锁定的构建依赖。
先审 dry-run，要求完整包集合匹配清单且 uv.lock 对应项全部来自 PyPI registry。
可选 kittentts/misaki 和 Android Git psutil 均不进入当前核心集合；macOS 使用
registry psutil 7.2.2。缺 wheel、需要构建、锁文件变化或来源不符时停止，不放宽限制。

## 从空目录准备（macOS arm64）

以下是手工、小步运行的 L02a 配方，尚非 L1 正式安装器。已有环境先运行末尾的只读
检查；不要为重跑而删除现有目录。空目录安装期间可联网，且须有下载授权。
在仓库根目录执行，要求现有 Python 能创建 bootstrap venv、Git 可访问公开 fork。

1. 创建私有 bootstrap，按哈希安装 uv；不写全局 Python。

```sh
umask 0077
mkdir -p .local/harness-lab/probe
python3 -m venv .local/harness-lab/probe/bootstrap
.local/harness-lab/probe/bootstrap/bin/python -m pip --isolated install \
  --no-cache-dir --require-hashes --only-binary=:all: --no-deps \
  -r requirements-probe-bootstrap.txt
```

2. 清空继承环境，固定缓存、Python 和依赖位置。不要加入模型凭据。
   若网络需要自定义代理/证书，先单独审查所需变量，不直接继承整个环境。

```sh
probe_uv() {
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin \
    UV_CACHE_DIR="$PWD/.local/harness-lab/probe/cache" \
    UV_PYTHON_INSTALL_DIR="$PWD/.local/harness-lab/probe/python" \
    UV_PROJECT_ENVIRONMENT="$PWD/.local/harness-lab/probe/venv" \
    "$PWD/.local/harness-lab/probe/bootstrap/bin/uv" "$@"
}
probe_uv --version
probe_uv python install 3.14.10 --no-bin --managed-python --no-config --system-certs
```

3. 获取固定源码。首次准备才执行 clone，已有目录不覆盖；不运行源码脚本。

```sh
git clone --no-checkout --no-recurse-submodules \
  https://github.com/jolearningusa/hermes-agent.git .local/harness-lab/probe/source
git -C .local/harness-lab/probe/source checkout --detach \
  557254faa24ef5d86f67595c4c64dc61644d0f68
```

4. 对空依赖环境 dry-run，先校验解析集合和源码。检查失败即停止，不执行下一步。
   dry-run 不执行安装；日志中的完整新增集合应恰好为 66 项。已有依赖环境不适用此
   空目录断言，直接执行第 6 步检查。

```sh
probe_uv sync --project .local/harness-lab/probe/source --python 3.14.10 \
  --managed-python --frozen --no-dev --no-default-groups --no-install-project \
  --no-build --no-python-downloads --no-config --system-certs --dry-run \
  > .local/harness-lab/probe/sync-dry-run.log 2>&1
```

```sh
python3 -I scripts/check_probe_runtime.py \
  --resolution-log .local/harness-lab/probe/sync-dry-run.log
```

5. 仅在 dry-run 和检查均退出 0 后安装；uv 校验 uv.lock 中的 wheel 哈希。

```sh
probe_uv sync --project .local/harness-lab/probe/source --python 3.14.10 \
  --managed-python --frozen --no-dev --no-default-groups --no-install-project \
  --no-build --no-python-downloads --no-config --system-certs \
  > .local/harness-lab/probe/sync-install.log 2>&1
```

6. 使用依赖环境自己的解释器和 `-I` 做只读检查。输出只含固定版本、计数、状态及
   提交，不含路径或内容；退出 0 才表示本切片通过。脚本不导入 Hermes 或安装的包，
   只读 distribution metadata、源码与锁文件，并用 Git 查询提交/工作区状态。

```sh
.local/harness-lab/probe/venv/bin/python -I scripts/check_probe_runtime.py
make check
```

预期 `mode=installed-runtime`、`result=pass`、66 个包、6 个文件哈希通过、源码干净，
Python/平台匹配清单。缺包、多包、版本漂移、重复 distribution、Git/直链来源、错误
Python/平台、文件哈希变化、脏源码或错误 commit 均失败。CI 只跑无下载的回归测试，
不要求 Linux CI 安装这个 macOS 运行时。

## 本次证据、限制与回滚

[运行证据](../evidence/l02a-runtime.json) 记录 2026-11-16 本机安装后复核结果。
bootstrap uv 版本核对为 0.13.8；managed Python 3.14.10；66 个包匹配清单且来自
锁文件中唯一的 PyPI 项，六个源码哈希及干净 commit 匹配；随后离线 frozen sync
退出 0（Checked 66 packages），只读检查再次通过。原始安装日志留在忽略目录，
不提交本机路径。分发包哈希由 uv 安装时按 uv.lock 验证；只读检查不重新哈希每个已安装
文件，也不构成依赖漏洞审计或全文件系统隔离证明。

本次未下载模型、Ollama 或 extras，未启动 Agent、未发生模型调用。L02 尚未通过；
L02b 仍需本地 mock、工具循环、组装来源与 wire request 逐字段匹配、强制摘要辅助
调用及实际沙箱验证。未验证 8 GiB 上真实模型性能，不进入 L1。

无共享存储迁移。回滚仅在确认无运行进程后删除本实验拥有的 probe 目录；不得删除
其他实例或修改系统 Python。ADR 的 7 天保留、512 MiB 配额作用于 session 调试数据，
不包含源码/解释器/依赖安装。此次 probe 安装目录实测约 738 MiB（du），需预留磁盘；
没有 session 数据。安装日志同样不作长期存储；本步骤未提供自动清理或调试配额执行器，
后续运行器须实现，不把设计当作已执行。
