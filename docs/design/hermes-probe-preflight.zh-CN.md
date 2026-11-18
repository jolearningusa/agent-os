# L02b 执行前依赖与源码预检

日期：2026-11-17。承接 [运行时准备](hermes-probe-runtime.zh-CN.md) 和
[交付计划](../plans/local-harness-deliveries.zh-CN.md)。本切片不执行 Hermes 或模型。

## 决策与信任边界

PR #30 已合并，评审新增低严重度发现：Git index 的 assume-unchanged / skip-worktree
能隐藏已跟踪源码的修改。执行前审核除状态检查外，读取 `git ls-files -v -z`，拒绝所有
小写状态与大写 S（含两标记同时存在），不修改 index、不清理文件。

依赖完整性采用先前设计允许的重建方案，不信任原 venv 里版本相同就意味着内容相同。
从已接受的 uv.lock 导出 66 个核心包的全部 wheel 哈希，仅允许唯一 PyPI registry 项；
用现有 bootstrap pip 24.2 和 managed Python 3.14.10 的兼容标签选择 wheel，只下载。
工具不升级，下载属于用户此前授权的同一固定核心依赖，不包含任何模型或 extras。

新增标准库脚本 `scripts/probe_dependencies.py`：先校验 uv.lock 与 harness.lock 中的
SHA-256，再按已审核核心清单选择 registry 项。export 输出 hash requirements；verify
要求目录只有每包一个已锁定 wheel，拒绝多包、少包、同包重复、目录、符号链接、非批准
文件名和不符哈希，输出安装清单或内容无关摘要。脚本不安装、解包或导入这些包。

在全新 execution-venv 中，uv 以 no-cache/no-index/offline/no-deps/require-hashes 和
only-binary 安装已核验 wheel，禁用源码构建。固定 uv 将 only-binary 与 no-build 视为
互斥参数，因此只使用前者，不叠加二者。下载与执行严格分阶段；下载可联网，后续
Agent 执行仍必须等待 mock 地址限制与实际沙箱验证。原 venv 不改动。

这证明安装输入来自锁定 artifact，**不是原 venv 全文件完整性检查**，也不防御拥有同一
用户权限的进程在检查后篡改文件。执行器必须在启动前重跑 artifact/source 预检并使用新建
受控环境，不把历史 pass 当作永久保证；解释器/uv/bootstrap pip 本身为已有可信工具边界。

## 小步运行方式

在仓库根目录、同一 shell 执行；已有目录不覆盖，失败立即停止。私有根目录 0700，写入
进程设 umask 0077。模型、Ollama 和 extras 不下载。以下命令不启动 Agent。

```sh
umask 0077
python3 -I -B scripts/probe_dependencies.py export \
  > .local/harness-lab/probe/core-wheel-requirements.txt
```

下载使用 managed 裸解释器选择标签，不使用尚未验证的依赖 venv；pip 不在目标中安装。
首次下载可联网。先确认 verified-wheels 与 execution-venv 不存在；已有目录时不执行
download/venv 步骤，只做 verify 或由用户识别后重建，不覆盖未知文件。

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin PIP_CONFIG_FILE=/dev/null \
  .local/harness-lab/probe/bootstrap/bin/python -m pip --isolated \
  --python .local/harness-lab/probe/python/cpython-3.14.10-macos-aarch64-none/bin/python3.14 \
  download --index-url https://pypi.org/simple --keyring-provider disabled \
  --no-cache-dir --no-deps --require-hashes --only-binary=:all: \
  --disable-pip-version-check --no-input \
  -r .local/harness-lab/probe/core-wheel-requirements.txt \
  -d .local/harness-lab/probe/verified-wheels
```

```sh
python3 -I -B scripts/probe_dependencies.py verify \
  --wheel-dir .local/harness-lab/probe/verified-wheels --requirements \
  > .local/harness-lab/probe/selected-wheel-requirements.txt
```

只有上一检查退出 0 后创建新环境。uv/python/cache 的隔离变量沿用运行时准备中的
probe_uv 函数（见运行时准备第 2 步），清空继承环境且缓存不落入用户全局目录。
以下显式指定解释器与目标路径，不使用已有用户 venv。

```sh
probe_uv venv --offline --no-config \
  --no-python-downloads \
  --python .local/harness-lab/probe/python/cpython-3.14.10-macos-aarch64-none/bin/python3.14 \
  .local/harness-lab/probe/execution-venv
```

```sh
probe_uv pip install --offline --no-config \
  --no-cache --no-index --no-deps --require-hashes --only-binary=:all: \
  --python .local/harness-lab/probe/execution-venv/bin/python \
  --find-links .local/harness-lab/probe/verified-wheels \
  -r .local/harness-lab/probe/selected-wheel-requirements.txt
```

```sh
python3 -I -B scripts/probe_dependencies.py verify \
  --wheel-dir .local/harness-lab/probe/verified-wheels
.local/harness-lab/probe/execution-venv/bin/python -I -B scripts/check_probe_runtime.py
make check
```

摘要预期 66 个 wheel、来源/哈希通过，execution-venv 的 66 个包与固定源码匹配。
全部成功仍不关闭 L02。原 venv 仍不作完整性保证；新环境实际执行的网络/文件隔离、
工具循环、上下文逐字段匹配和摘要辅助调用由后续切片完成。

## 验证与回滚

无网络测试使用合成 wheel 字节（不加载），覆盖哈希变化、错误来源、额外/缺少/重复包、
符号链接与目录；源码回归使用真实临时 Git 仓库覆盖两种 index 标记及同时设置。
真实下载只在已授权的本机运行，不进入 CI。不得通过跳过校验、源码构建或升级来恢复。
失败不修改旧环境；回滚在确认无进程后仅移除本切片拥有的 wheel/requirements/新 venv，
不删除其他实例。安装 artifact 不计入 session 调试配额，另行预留磁盘；调试保留与清理
仍由 L1/L3 实现。

本机实际下载、离线安装与新环境审核均已通过，见 [本次证据](../evidence/l02b-preflight.json)。
wheel 目录约 39 MiB、新 venv 约 121 MiB；历史环境与安装证据不覆盖。
