# Metadata Forensics：B01–B05 Python 项目

将提供的五份 notebook 重构为可导入模块和命令行程序。运行不需要 Jupyter、IPython 或原始 notebook；原文件未改动。文档中的指令作为实验资料保留，不作为本次操作授权。

## 安装与运行

在本项目目录运行（Python 3.10+）：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

# B01：40 人、无时间范围 blocking
metadata-forensics b01

# B02：4000 人，四种方法；只运行冻结基线可加 --methods nearest
metadata-forensics b02

# B03：10 个主实验条件 + 3 个独立 fragmentation 诊断
metadata-forensics b03

# B04：默认三个条件；--full 扩展为十个条件
metadata-forensics b04

# B05：离线准备证据与提示词，不生成假的模型报告
metadata-forensics b05 --case outputs/b04/example_investigation.json

# 显式调用模型；先在环境变量中设置 DEEPSEEK_API_KEY
metadata-forensics b05 --case outputs/b04/example_investigation.json --live --provider deepseek
```

`python -m metadata_forensics` 与 `metadata-forensics` 等价。尚未安装包时，也可在项目根目录用 `PYTHONPATH=src python -m metadata_forensics ...`。

快速检查可给 B02–B04 加 `--n-patients 40`。这只是运行检查，不是 N=4000 的正式研究结果。默认种子 42，可用 `--seed` 修改。`--output` 指定输出目录；重复使用同一目录会覆盖同名结果，建议不同配置使用不同目录。

B05 支持 `--provider deepseek|openai|ollama`、`--model`，兼容环境变量 `B05_PROVIDER`、`B05_MODEL`、`B05_BASE_URL`。OpenAI 使用 `OPENAI_API_KEY`，Ollama 不需要密钥。模型和端点默认值沿用源 notebook，未验证当前服务可用性。找不到 `--case` 时直接报错，不会替换成演示病例。

## 目录与职责

```text
src/metadata_forensics/
  synthetic.py       合成数据；保持原始随机数调用顺序
  matching.py        时间范围 blocking、四种评分与排序
  corruption.py      日期偏移、缺失、错配、ID fragmentation
  evaluation.py      全体真值分母、可观测性、alias-aware 指标
  investigation.py   top-two 反事实、事件定位、确定性证据报告
  reporting.py       证据白名单、模型调用、输出校验与审计
  pipeline.py        B01–B04 流程编排、CSV/JSON/PNG 输出
  cli.py             命令行入口
  __main__.py        python -m 入口
tests/               回归与边界检查
docs/                原始实验说明、来源哈希、迁移及验证记录
validation/          本次实际运行的指标与离线证据样例
```

主要输出：B01/B02 的 `metrics.csv`、各方法 `*_top10.csv`；B03 的 `b03_results.csv`、`fragmentation_diagnostic.csv` 和退化曲线；B04 的决策表、事件怀疑度、review 分组诊断、定位图与 `*_investigation.json`；B05 的 `prepared_evidence.json`，或 live 模式下的审计 JSON 与 Markdown 报告。中间条件完成即保存 `*_results_partial.csv`，但目前不支持自动断点续跑。

真值 crosswalk、corruption manifest 与逐身份评估放在 `evaluation_only/`。匹配器只接受观测数据，LLM 只接受白名单证据字段。`MATCH` 沿用上游启发式决策，不代表身份已被确认，也不自动修改任何原始记录。

## 保留的实验定义与限制

- B02–B04：30 天范围 blocking、±2 天命中、同日 PB/BM 合并为一个时间事件。
- B02c 保留 `alignment_cost` 排序项；B02d 从 sequence alignment 的结果估计全局背景命中率。
- 排名平局统一采用 `lab_id` 升序，与 B03/B04 一致；N=4000、seed=42 的 B02a 与原文全部主要指标一致。
- B03 主循环实际是 10 个条件，另有 3 个 fragmentation 诊断；原 notebook 标题把主循环写成 13，已在使用说明中澄清。
- B04 衡量原始 top-two 候选之间的删日期敏感性，不是完整候选集的重新匹配。没有第二候选时 instability 缺失并进入 REVIEW。
- 事件定位只覆盖当前 top-1 配对中的可见样本；不能定位被删除的行。稳定性、margin 及 `MATCH` 都不是校准概率。
- 模型校验覆盖结构、候选顺序、样本归属与证据角色，不能证明自然语言陈述完全正确。
- 默认使用完整候选表，N=4000 的各方法和多条件实验耗时、占用内存明显高于 40 人检查。

## 测试

```bash
python -m unittest discover -s tests -v
```

实际验证范围与版本见 [验证记录](docs/VALIDATION.md)，迁移说明见 [迁移记录](docs/MIGRATION.md)。
