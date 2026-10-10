# 实际验证记录

日期：2026-10-11（Asia/Tokyo）。依赖版本记录在 `validation/environment.json`；可用 `requirements-tested.txt` 固定此次验证所用的科学计算库版本。测试使用当前工作区已有 Python 环境，未创建新的安装环境。

## 已通过

- 8 项 unittest：生成可重复性、三种基础评分的 blocking 前后全表等价、全体真值分母与空候选、污染操作独立性及 manifest、B04 到 B05 证据边界、空诊断、模型决策/证据角色校验、模拟 HTTP 响应下审计与 Markdown 导出。
- 全部 Python 模块 compileall。
- B01：40 人完整运行。
- B02：40 人四种方法完整运行；4000 人 seed=42 的 nearest 完整运行。
- B03：40 人，10 个主条件与 3 个 fragmentation 诊断完整运行，CSV 和 PNG 已生成。
- B04：40 人，10 个条件完整运行，决策、定位、review 诊断、JSON 和 PNG 已生成。
- B05：实际 B04 JSON 的离线证据准备运行通过；网络传输仅做 mock 测试。

## 4000 人 B02a 对照

| 指标 | 本次 Python 实测 | Baseline.md |
|---|---:|---:|
| Retrieval | 0.978 | 0.978 |
| Top-1 | 0.84825 | 0.84825 |
| Top-3 | 0.93950 | 0.93950 |
| Top-10 | 0.97750 | 0.97750 |
| MRR | 0.8969848394660894 | 0.89698 |

**归因修正：**本次共有 4000 个真值身份、3912 个可观测实验室身份，88 个无样本身份，`n_blocked_out=0`，可观测身份的 blocking recall 为 1.0。因此这次复现的 2.2% 检索损失来自无样本，而非范围 blocking。原 `Baseline.md` 将这部分归因于 blocking，不受本次分解指标支持。原文已原样保留，便于追溯。

## 尚未验证

未执行 4000 人 B02b/c/d 与完整 B03/B04；40 人测试不能证明它们的完整规模研究结论。未调用真实 DeepSeek/OpenAI/Ollama 服务，未验证实际模型文本质量。未人工审查输出图的视觉质量。未测试全新虚拟环境安装或构建 wheel。

`validation/` 保存精选实测结果，不包含大体积候选表。B05 prepared_evidence 记录的 source 路径是本次临时运行路径，完整证据已内嵌，不影响审计；正常使用请按 README 自行运行 B04。
