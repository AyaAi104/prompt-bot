# prompt-bot

[English documentation](readme.md)

`prompt-bot`  是一个可复用的 Codex 技能包，用于开展由需求规格驱动、人工参与关键决策的软件开发。它引导编码智能体先澄清需求，再按照确认后的规格实现和测试，并在需要人工判断时暂停相关工作、请求用户决定。

项目包含智能体指令、参考文档、规格模板和两个 Python 命令行工具。脚本负责检查规格与记录检查点，具体开发流程由智能体执行。脚本不会自动拦截工具调用，也不提供文件系统权限隔离。

## 运行要求

- Python 3.10 或更高版本。
- 仅使用 Python 标准库，无需执行 `pip install`。
- 以下命令默认在本项目目录运行，使用 `python`。如果环境中的 Python 3 命令为 `python3`，请相应替换。

## 项目文件

```text
.
├── SKILL.md
├── readme.md
├── readme_cn.md
├── references/
│   ├── five-element-rubric.md
│   ├── hitl-hook-protocol.md
│   ├── clarification-and-research.md
│   ├── pipeline-and-verification.md
│   └── manual-chat-handoff.md
├── assets/
│   ├── spec-contract.template.md
│   ├── tasks.template.md
│   ├── progress.template.md
│   ├── handoff.template.md
│   └── coding-prompt.template.md
├── scripts/
│   ├── validate_spec.py
│   └── hitl_checkpoint.py
└── tests/
    └── test_skill_scripts.py
```

| 文件 | 功能 |
| --- | --- |
| [SKILL.md](SKILL.md) | 技能入口，定义触发场景、五阶段状态机、需求澄清门槛、实现与测试循环、人工检查点和最终验收流程。 |
| [references/five-element-rubric.md](references/five-element-rubric.md) | 五类需求的评估规则、不明确需求的示例、建议提问方式，以及规格文件的格式约定。 |
| [references/hitl-hook-protocol.md](references/hitl-hook-protocol.md) | 各类钩子的触发条件、中断卡片、检查点 JSON 结构、暂停与恢复规则，以及日志写入失败时的处理方式。 |
| [references/clarification-and-research.md](references/clarification-and-research.md) | 缺信息先提问，以及用户不知道时的检索、分析和确认分支。 |
| [references/pipeline-and-verification.md](references/pipeline-and-verification.md) | S/M/L 分级、定向探索、纵向切片和验证方式选择。 |
| [references/manual-chat-handoff.md](references/manual-chat-handoff.md) | 用户手动开启新聊天的交接材料、审查与恢复规则。 |
| [assets/tasks.template.md](assets/tasks.template.md) | 纵向任务清单，记录验收编号、依赖、命令和结果。 |
| [assets/progress.template.md](assets/progress.template.md) | 持久化已完成工作、决定、失败、阻塞和下一步。 |
| [assets/handoff.template.md](assets/handoff.template.md) | 记录精确文件、快照身份、命令和可复制的新聊天 Prompt。 |
| [assets/coding-prompt.template.md](assets/coding-prompt.template.md) | 分离背景、参考样板、带原因的约束和执行任务。 |
| [assets/spec-contract.template.md](assets/spec-contract.template.md) | 任务规格模板，包含版本号、锁定状态、五项需求状态和章节标题。模板在填写完成前会校验失败，这是预期行为。 |
| [scripts/validate_spec.py](scripts/validate_spec.py) | 检查规格结构、必填内容、需求状态及未解决的占位标记，输出 JSON 诊断信息。 |
| [scripts/hitl_checkpoint.py](scripts/hitl_checkpoint.py) | 输出人工介入提示，保存检查点历史，并记录用户决定以解除当前检查点。 |
| [tests/test_skill_scripts.py](tests/test_skill_scripts.py) | 在临时目录中测试命令行工具，覆盖有效和无效规格、检查点生命周期、损坏状态及并发访问锁。 |
| [readme.md](readme.md) / [readme_cn.md](readme_cn.md) | 项目的英文与中文说明文档。 |

工作区原有的 `main.py` 和 `.idea/` 不属于技能包的必需文件。两个 Python 工具均不通过 `main.py` 启动。

## 工作流程

每份规格必须明确以下五个维度：

| 维度 | 需要明确的内容 |
| --- | --- |
| Goal（目标） | 要构建什么、服务谁，以及核心行为。 |
| Constraints（约束） | 运行环境、依赖限制、架构边界及相关运行限制。 |
| Input（输入） | 数据结构、参数、事件、前置条件及非法输入的处理方式。 |
| Output（输出） | 返回值、生成文件、错误表现及状态变更。 |
| Acceptance Criteria（验收标准） | 可观察、可判定通过或失败的条件，使用 `AC-1`、`AC-2` 等编号。 |

智能体按照五个阶段开展工作：

1. **PARSE_SPEC：解析规格。** 从用户请求和工作区信息中提取五项需求。
2. **CLARIFY_GATE：澄清需求。** 解决不明确的问题，编写 `.codex/active-spec.md`，锁定并校验规格。每轮集中提出不超过五个关键问题。
3. **BUILD_AND_VERIFY：实现与验证。** 拆分任务，将测试映射到验收标准，执行实现和测试；项目已有代码检查工具时，运行相应检查。
4. **HITL_INTERRUPT_HOOK：人工介入。** 当重要决策或失败需要用户判断时，暂停受影响的工作。此阶段按条件触发，不要求每一步开发都经过人工确认。
5. **ACCEPTANCE_SIGN_OFF：交付验收。** 逐项展示验收证据，请用户确认结果或提出修改意见。

只有 `CLEAR` 状态可以通过需求门槛。`MISSING`（缺失）、`AMBIGUOUS`（有歧义）和 `INFERRED_NEEDS_CONFIRMATION`（推断但待确认）都会阻止应用实现。已经确认的需求和已经授权的操作无需重复审批；规格发生实质变化时，需要更新版本、重新澄清并校验。

## 如何使用

请编码智能体读取项目中的 `SKILL.md`，并将流程应用于具体任务。例如：

> 读取本项目的 SKILL.md，按照 prompt-bot 流程开发一个 Python 命令行工具，将 CSV 库存数据转换为 JSON。实现前先澄清缺失的需求。

需求门槛通过之前，可以进行只读调查和规格起草。需求确认、规格锁定且校验通过之后，再开始编写应用实现代码。

以下命令默认技能脚本与目标工作区位于同一目录。将技能用于其他项目时，应在目标工作区执行命令，并使用技能脚本的绝对路径；运行时文件应归属于目标项目。

## 校验需求规格

将 `assets/spec-contract.template.md` 复制到 `.codex/active-spec.md`，必要时先创建 `.codex` 目录。根据确认后的需求填写五个核心章节，以及 Scope、Interfaces 和 Verification 三个补充章节。保留模板中的英文二级标题和元数据字段名，章节正文可以使用中文或其他语言。

新规格使用 `format_version: 2`，并设置 `size: S`、`M` 或 `L`。未声明版本或显式使用版本 1 的旧规格仍可校验，实质修订时应升级；未知版本会被拒绝。

校验前，将五项状态设为 `CLEAR`，将 `locked` 设为 `true`，并确保 `revision` 是正整数。验收标准应包含 `AC-1` 等编号。

```sh
python scripts/validate_spec.py .codex/active-spec.md
```

| 退出码 | 含义 |
| --- | --- |
| `0` | 结构校验通过，JSON 中包含 `"ready": true`。 |
| `2` | 需要进一步澄清或修正，或输入文件无法读取。文件与内容检查会返回 JSON 诊断；命令行参数使用错误时，由 argparse 输出用法提示。 |

校验器会拒绝空白或重复的必需章节、非 `CLEAR` 状态、未锁定规格、`TODO`、`TBD`、`???` 等未解决标记，以及未闭合的代码块或 HTML 注释。代码示例或注释中的标题不能代替必需章节。

文件头采用受限的 YAML 子集，只支持未加引号的标量字段、空行及整行注释，不支持带引号的值、行内注释、嵌套 YAML 或块标量。校验通过代表结构完整；智能体仍需检查需求是否有实际含义、相互一致，以及测试是否覆盖目标行为。

## 人工检查点

| 钩子 | 使用场景 |
| --- | --- |
| `PRE_CODE_SPEC_LOCK` | 拟定规格仍需用户确认。 |
| `ARCH_DECISION_HOOK` | 重要架构选择或未获批准的数据结构变更需要用户决定。 |
| `HIGH_RISK_OP_HOOK` | 操作尚需授权，例如删除已有文件、修改生产配置、安装外部依赖或运行迁移。 |
| `TEST_TRIAGE_HOOK` | 同一根因导致验证连续失败三次，或发现规格本身存在矛盾。 |
| `SCOPE_DRIFT_HOOK` | 必要行为超出了已锁定的约束或输入范围。 |
| `FINAL_ACCEPTANCE_HOOK` | 必需验证和独立审查已完成处理，等待用户验收。 |
| `NEW_CHAT_REVIEW_HOOK` | 暂停，等待用户手动开新聊天独立审查；需交接文件及后续报告。 |
| `CONTEXT_HANDOFF_HOOK` | 暂停，等待用户手动开新聊天续做或调研；需交接文件。 |

创建检查点：

```sh
python scripts/hitl_checkpoint.py --hook-type ARCH_DECISION_HOOK --summary "选择持久化存储方案" --options "SQLite,JSON 文件" --evidence "AC-3 要求支持并发写入" --recommendation "SQLite" --phase BUILD_AND_VERIFY
```

`--options` 必须包含两个或三个不同的非空选项，使用英文逗号分隔，选项内部不能包含英文逗号。默认推荐第一个选项。命令会输出检查点 ID 和结构化中断提示；智能体需要在聊天中展示待决策事项，并等待用户实际回复。

收到用户回复后，将 `CHECKPOINT_ID` 替换为刚才输出的 ID，记录用户的真实决定：

```sh
python scripts/hitl_checkpoint.py --resolve CHECKPOINT_ID --decision "用户选择 SQLite，并同意相应规格修订"
```

检查点命令在记录成功时返回 `0`，参数错误、状态异常、锁冲突或文件系统错误时返回 `2`。成功创建检查点表示工作应当暂停，并不代表获得授权。记录解决结果也不会自动重启智能体，或自动校验修改后的规格。

## 保留问答模式与手动新聊天

缺少必要信息时，AI 先向用户提问。用户回答“不知道”后，AI 才进入相应的检索或分析分支：核对已有证据，必要时搜索官方或一手来源，或分析稳定的技术取舍，给出建议及不确定性。不会编造私人业务规则，也不会将沉默当作同意。明确授权 AI 决定的事项可在授权边界内继续，其他重要决定仍需确认。

S 级任务保留简短的五要素门槛，信息齐全时不做重复访谈；M 级增加持久化计划和纵向切片；L 级必须独立审查。M/S 级在用户要求或接口与风险需要时也进入独立审查。根据实际项目选择测试、构建、类型检查、lint 和 UI 截图对比。

需要新上下文或交叉验证时，AI 会先保存交接材料，然后**暂停任务**，礼貌提醒你在同一工作区手动开启新聊天，提供准确的文件路径、可直接复制的 Prompt，以及需要带回的报告。AI 不自行清理或压缩当前聊天，不自动创建聊天，也不使用子智能体代替这次独立审查。新聊天以只读审查模式工作，不会递归要求再开一个审查聊天。

准备好真实交接文件后：

```sh
python scripts/hitl_checkpoint.py --hook-type NEW_CHAT_REVIEW_HOOK --summary "需要独立审查" --options "手动开启新聊天,先讨论阻塞" --handoff-file .codex/handoff.md --phase WAIT_FOR_USER_NEW_CHAT
```

你带回真实报告后，原聊天根据你的决定记录结果：

```sh
python scripts/hitl_checkpoint.py --resolve CHECKPOINT_ID --decision "用户带回审查报告，继续处理发现" --review-report .codex/review-report.md
```

新增检查点会记录文件绝对路径与 SHA-256。报告缺失、为空、不可读取或不是有效 UTF-8 时，不能解除审查检查点。收到报告不代表审查通过，AI 仍需核对快照并处理问题；脚本不能认证报告作者或判断报告质量。原有检查点命令和旧规格格式继续兼容。

## 运行时文件

| 路径 | 功能 |
| --- | --- |
| `.codex/active-spec.md` | 智能体从模板生成的当前任务规格。 |
| `.codex/tasks.md` | M/L 任务的纵向切片计划。 |
| `.codex/progress.md` | 持久化进度、决定和阻塞。 |
| `.codex/handoff.md` | 交接文件清单、快照、命令和新聊天 Prompt。 |
| `.codex/review-report.md` | 独立审查发现和验证证据。 |
| `.codex-spec-state.json` | 保存检查点历史、当前检查点 ID、相关证据、时间戳和用户决定。 |
| `.codex-spec-state.json.lock` | 更新检查点状态时使用的临时独占锁文件。 |

这些文件在使用过程中生成，不是随项目提供的已完成任务状态。可以用 `--state-file PATH` 指定其他日志位置。每份状态文件只允许存在一个待解决检查点，解决后才能创建下一个。写入使用原子替换；状态损坏时会拒绝操作，不会清空历史重新开始。如果进程崩溃遗留锁文件，应先确认没有写入进程运行，再手动移除该锁。

## 验证方式

执行脚本测试套件：

```sh
python -m unittest discover -s tests -v
```

更新后的脚本套件已通过全部 26 项测试。测试使用隔离的临时工作区，覆盖完整与不完整规格、占位标记、错误元数据、Markdown 解析、文件缺失或读取失败、八种钩子、版本 2 规格、交接文件及报告要求、决策历史、无效请求、损坏状态、锁冲突和自定义日志路径。

这些测试验证的是辅助工具，不代表智能体一定会遵守全部指令，也不代表后续开发的应用已经满足验收标准。每个实际任务仍需自己的实现测试和验收证据。
