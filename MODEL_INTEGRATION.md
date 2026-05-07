# 生产模型接入说明

当前服务已经能运行，但默认检测器是轻量启发式 ensemble，适合 MVP、接口联调和报告流程验证。要做到商业可用的“高准确率”，需要把下面的模型检测器接入 `app/detectors/model_hooks.py`，并在融合层重新校准权重。

## 推荐检测器组合

1. 中文论文专用 Transformer 分类器
   - 训练目标：段落级 human / AI / mixed。
   - 推荐底座：Chinese-RoBERTa、MacBERT、DeBERTa-v3、ModernBERT 中文适配版本。
   - 数据必须覆盖摘要、引言、综述、方法、实验、结论。

2. Perplexity 检测器
   - 用一个中文学术语言模型计算 token 级负对数似然。
   - 输出低困惑度、高顺滑度风险。

3. Fast-DetectGPT / DetectGPT 类检测器
   - 对原文做扰动，比较概率曲率。
   - 适合零样本检测，但长论文成本较高。

4. Binoculars 类双模型检测器
   - 用 observer/performer 两个模型比较交叉困惑度。
   - 对跨模型生成文本有较好泛化潜力。

5. 风格与结构检测器
   - 当前启发式模块保留为解释层信号，不应作为唯一主判。

## 数据校准

至少准备：

- 人类真实中文论文段落。
- GPT、Claude、Gemini、DeepSeek、Kimi、通义、文心生成段落。
- AI 生成后人工修改段落。
- 人类写作后 AI 润色段落。
- 不同学科、不同学历、不同章节样本。

如果目标是预测知网风险，需要额外收集：

```text
同一篇论文原文
知网 AIGC 报告结果
本系统各检测器原始分数
```

然后训练校准模型，把本系统分数映射到“知网风险区间”，而不是宣称等同知网。

## 接入方式

实现一个 `Detector`：

```python
from app.detectors.base import Detector, DetectorResult


class TransformerAIGCDetector(Detector):
    name = "transformer_aigc"
    weight = 0.45

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        probability = model_predict(segment)
        return DetectorResult(
            name=self.name,
            score=probability,
            weight=self.weight,
            reasons=["Transformer 分类器判定该段 AI-like 概率较高"] if probability > 0.7 else [],
        )
```

然后在 `build_default_detectors()` 或服务启动配置中加入该检测器。

## 上线指标

不要只看 accuracy。建议核心验收指标：

- Precision
- Recall
- False Positive Rate
- False Negative Rate
- AUC
- Calibration Error
- 不同学科/章节/长度下的分层表现

论文场景里误判代价高，建议高风险阈值保守设置，并保留人工复核灰区。

