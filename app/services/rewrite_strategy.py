from __future__ import annotations

import re


LEARNED_REPORT_STRATEGY = """
【来自高AIGC版(88.79%)→低AIGC版(4.94%)、低查重版(1.73%)的对照策略】
这类成功降AIGC/降重不是靠同义词替换，而是靠“句骨重排 + 人话化 + 保留证据”：
1. 把过度工整、宏观、官方化的句子改成学生论文里更自然的说明句。减少“赋能、支撑、体系、机制、路径、持续拓展、坚实基础、落地价值、有效弥补、优化完善”等高频AI书面词。
2. 不删除核心事实，保留并强化可核验细节：版本号、框架名、数据库名、接口名、测试工具、并发数、响应时间、引用编号、业务模块名。
3. 改句子骨架，而不是只换词：把“X为Y提供了可靠支撑/重要参考”改成“X可以帮助Y完成某个具体步骤”；把“通过A实现B”改成“系统先做A，再得到B”。
4. 对技术定义和研究现状，避免百科式整齐定义；改为“这个技术在本系统里具体做什么、为什么选它、接在哪个模块上”。
5. 降重时保留观点但换表达路径：换主语、换动作顺序、合并或拆分长句、把抽象结论落到具体模块/数据/流程。
6. 输出必须少而准：只挑真正会拖高AIGC或重复率的2-4句，不要把正常句子也列成问题。
"""


HUMANIZE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("持续发展", "不断发展"),
    ("持续迭代", "不断更新"),
    ("趋于多元", "变得更加多样"),
    ("分散存储于", "分散在"),
    ("难以保证", "很难保证"),
    ("提供了新的技术解决路径", "提供了新的解决思路"),
    ("理论试点转向实际落地", "试点逐渐进入实际使用"),
    ("应用范围持续拓展", "使用范围也在扩大"),
    ("提供了坚实技术基础", "提供了技术基础"),
    ("有效弥补", "补上"),
    ("赋予", "加入"),
    ("支撑", "支持"),
    ("适配", "适合"),
    ("保障", "保证"),
    ("提升", "提高"),
    ("优化", "改进"),
    ("落地价值", "实际使用价值"),
    ("落地形式", "使用方式"),
    ("落地", "应用"),
    ("体系", "结构"),
    ("机制", "做法"),
    ("路径", "方法"),
)


ACTIONABLE_REWRITE_MARKERS: tuple[str, ...] = (
    "随着",
    "不断发展",
    "持续发展",
    "赋能",
    "支撑",
    "体系",
    "机制",
    "路径",
    "落地",
    "具有重要意义",
    "提供参考",
    "参考价值",
    "有效提升",
    "显著提高",
    "优化完善",
)


_DETAIL_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:%|ms|秒|s|个|人|次|年|月)|"
    r"SpringBoot|Springboot|Vue|MySQL|JWT|MyBatis|Postman|Docker|"
    r"API|RAG|ECharts|Element Plus|\[\d+\])",
    re.IGNORECASE,
)


def apply_learned_rewrite_style(text: str) -> str:
    rewritten = text
    for source, target in HUMANIZE_REPLACEMENTS:
        rewritten = rewritten.replace(source, target)
    return rewritten


def has_verifiable_detail(text: str) -> bool:
    return bool(_DETAIL_PATTERN.search(text))


def actionable_marker_count(text: str) -> int:
    return sum(text.count(marker) for marker in ACTIONABLE_REWRITE_MARKERS)
