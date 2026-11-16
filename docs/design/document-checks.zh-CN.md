# 文档检查契约（L06）

依据 [本地交付计划](../plans/local-harness-deliveries.zh-CN.md) 的 L06，将原先临时
运行的文档检查固定为标准库脚本。开发与评审均可从仓库根目录执行：

```sh
python3 scripts/check_docs.py
python3 -m unittest discover -s tests -p 'test_check_docs.py' -v
```

## 检查范围

检查仓库根目录、docs 下及 .github 根目录中的 Markdown。只读取文件，跳过代码围栏
内的链接和验收 ID；所有行仍检查尾随空白和结尾换行。围栏支持三个以上反引号或波浪号，
结束字符须与起始相同且长度足够。UTF-8 读取失败或未关闭围栏返回错误。

检查行内链接、图片链接及 reference link 的目标定义，离线验证相对目标存在并保持
在仓库范围内。带 fragment 的 Markdown 目标核对 ATX 标题锚点，支持中文、重复标题
后缀和百分号编码路径。HTTP/HTTPS、mailto 等外部目标保持离线跳过。Markdown
解析限于上述形式，复杂嵌套链接和自定义 HTML anchor 在未来新增 fixture 后再扩展。

验收定义来自 docs/plans 下行首列表中的 L00/V00 形式编号（仅示意模式，实际编号
须已定义）。全仓文档的编号引用必须能对应定义，定义不得重复。未完成状态不影响
编号存在性，脚本不将文档通过转换为功能验收完成。

## 失败行为与测试

默认仓库路径由脚本定位，可用 --root 指向测试仓库。从其他 cwd 调用结果保持一致。
错误输出相对文件路径、行号及规则，失败退出码 1，成功退出码 0。空检查范围、
越出仓库的路径和指向外部的符号链接拒绝，避免读取仓库范围外内容。

临时测试仓库覆盖正确文档、相对链接/锚点、失效链接、重复和悬空验收 ID、尾随空白、
缺换行、未关闭围栏与代码围栏内示例。破坏文档后断言 CLI 非零退出，恢复后断言 0，
证明失败没有被忽略。无网络测试确认检查仅依赖本地文件。

L06 本次交付脚本与正反例，L04 接入 make check 和 CI，并证明两处执行相同命令。

## L04a 统一入口与 PR #24 反馈

根目录 `make check` 顺序运行文档检查、配置/事件 CLI、完整 unittest 和 Python
语法编译。默认 Python 来自既有校验 venv，可用 `make check PYTHON=python3` 覆盖。
入口不安装依赖、不联网、不获取或运行 vendor 子模块。语法编译会产生被 Git 忽略的
Python 缓存。CI 接入与远端失败/恢复证据在 L04b 单独交付。

链接扫描屏蔽完整的行内反引号代码片段，保留换行供错误定位；验收编号引用仍检查
行内代码。含空格的目标须使用尖括号或百分号编码。裸空格目标按 GitHub 的非链接
文本处理，不作链接校验。CRLF 按 Python 文本读取归一化为 LF，CR 不单独算尾随空白，
空格后接 CRLF 的尾随空白仍报错。

自我改进记录中的“预防规则汇总”连续编号之间须无空行，其余章节的 Markdown
列表保持原有规则。这个检查落实重复格式错误的预防要求。

本次失败传播验证在临时副本中执行，复制 Makefile、scripts、configs、schemas、tests、
harness.lock.json 和 L0a 源码清单，解释器显式指向已安装依赖的校验 venv。将临时
README 写为带尾随空格的内容后，make check 返回 2；恢复合法 README 后返回 0。
真实仓库文件保持原状。该验证证明本地入口失败传播，远端 CI 结果仍由 L04b 提供。

## L04b CI 接入

行内代码配对限定在同一空行分隔段落，保持原始偏移，单段内多行代码仍支持。
CI 使用 ubuntu-24.04 / CPython 3.13.0 和已固定 SHA 的官方 checkout/setup-python，
只授予 contents: read，关闭凭据持久化和 submodule 获取；无秘密或部署环境输入。
依赖安装是独立准备步骤，使用 --require-hashes 和二进制 wheel；之后运行
`make check PYTHON=python`，与本地入口相同，检查本身保持离线。

首次验证保持 PR 为 Draft，提交一次受控无效配置以确认门禁失败，恢复后再次运行。
失败、恢复和最终 head 的 run 链接记录在 PR，只有最终 CI 通过后才 ready。
本步骤不配置仓库 ruleset，检查成为 required status 需维护者另行授权。

官方 Action 提交分别为 checkout v6 `d23441a48e516b6c34aea4fa41551a30e30af803` 和
setup-python v6 `ece7cb06caefa5fff74198d8649806c4678c61a1`，由官方 API 解析确认。
[checkout](https://github.com/actions/checkout)、[setup-python](https://github.com/actions/setup-python)

Linux 的 rpds-py 2026.9.1 cp313 x86_64 manylinux wheel SHA-256 来自 PyPI 发布元数据，
CI 安装时由 pip 核验；其余纯 Python wheel 复用现有哈希。[PyPI 元数据](https://pypi.org/pypi/rpds-py/2026.9.1/json)

实测失败与恢复的 run、head、工作流及依赖哈希见 [CI 证据](../evidence/l04b-ci.json)。
该文件记录观察到的两次运行；最终 PR head 在 ready 前还须独立检查其最新状态。
