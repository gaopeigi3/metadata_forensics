# 迁移记录

| 原文件 | Python 对应部分 |
|---|---|
| baseline01.ipynb | synthetic.generate、b01（40 人，无 blocking） |
| baseline02.ipynb | matching、evaluation、b02 四种方法 |
| B03_Controlled_Corruption.ipynb | corruption、b03、alias-aware 诊断 |
| B04_Counterfactual_Evidence_Reliability.ipynb | Investigator、b04 |
| B05_LLM_Forensic_Investigation.ipynb | reporting、b05 |
| Baseline.md | 原样保存于 docs/Baseline.md |

实际重构：提取重复生成器和算法函数；将全局 clinical_timelines 改为 Investigator 实例参数；移除 notebook display、裸表达式和导入时运行；数据在内存传递，输出路径显式配置。所有实验由 CLI 调用，包导入不写文件、不请求网络。

修复原始 pd/np 导入顺序依赖；空候选评估 rank 显式转换为数值；空反事实及事件定位返回带列空表；范围 blocking 向量化，保持候选顺序及判定条件。随机生成器使用局部 Random，保留原随机调用序列。新增配置和来源哈希。

B05 使用标准库 urllib 替换 requests；不再依赖 IPython；默认离线，不自动调用 API；缺少病例报错，不回退演示病例；无效模型输出保留审计，不导出正式 Markdown。增加候选顺序、数据类型、证据角色校验。

原始研究笔记保留在 docs 中，其中“运行 notebook”“切换 QUICK”等是历史说明；当前操作以 README 和 CLI --help 为准。原稿中的实验结论未视为已被代码验证，参见 VALIDATION。
