from app.config import Settings
from app.plagiarism.scoring import score_duplication
from app.services.analyzer import PaperAnalyzer
from app.services.text_processing import clean_body_text, segment_document


def test_analyze_returns_segments_and_score() -> None:
    text = (
        "随着人工智能技术的发展，教育评价体系正在发生深刻变化。"
        "本文首先分析人工智能赋能教育评价的理论基础，其次讨论现实问题，最后提出优化路径。"
        "该研究具有重要意义，并能为相关实践提供参考价值。\n\n"
        "访谈记录显示，三位教师在实际课堂中主要使用形成性评价表。"
        "其中两位教师提到学生反馈会影响下一轮教学设计。"
        "这些材料来自 2024 年 10 月至 11 月的校内调研。"
    )

    analyzer = PaperAnalyzer(Settings())
    result = analyzer.analyze(text, "demo")

    assert result.segment_count >= 1
    assert 0 <= result.ai_like_score <= 1
    assert (
        0 <= result.predicted_cnki_range.lower <= result.predicted_cnki_range.upper <= 1
    )
    assert result.confidence > 0
    assert result.total_chars > 0
    assert result.segment_reports
    assert result.disclaimer


def test_reference_section_is_stripped() -> None:
    text = (
        "本文基于问卷数据分析学生学习行为。样本来自三所高校，共回收问卷 386 份。"
        "研究发现，课堂反馈频率与学习投入之间存在正相关关系。\n\n"
        "参考文献\n"
        "[1] 张三. 人工智能教育研究. 北京: 某出版社, 2020."
    )

    analyzer = PaperAnalyzer(Settings())
    result = analyzer.analyze(text)

    assert result.total_chars < len(text)


def test_clean_body_text_removes_toc_page_noise_and_acknowledgements() -> None:
    text = (
        "论文标题\n"
        "1\n"
        "目录\n"
        "摘要 ........ 1\n"
        "第一章 绪论 ........ 2\n\n"
        "摘要\n\n"
        "本文基于问卷数据分析学生学习行为。样本来自三所高校，共回收问卷 386 份。"
        "研究发现，课堂反馈频率与学习投入之间存在正相关关系。\n\n"
        "致谢\n"
        "感谢导师和同学。"
    )

    cleaned = clean_body_text(text)

    assert "目录" not in cleaned
    assert "感谢导师" not in cleaned
    assert "回收问卷 386" in cleaned


def test_segment_document_keeps_section_and_paragraph_index() -> None:
    text = (
        "第一章 绪论\n\n"
        "本文基于问卷数据分析学生学习行为。样本来自三所高校，共回收问卷 386 份。"
        "研究发现，课堂反馈频率与学习投入之间存在正相关关系。"
        "在后续访谈中，教师还补充说明评价表会根据课堂主题进行调整。\n\n"
        "第二章 方法\n\n"
        "访谈记录显示，三位教师在实际课堂中主要使用形成性评价表。"
        "其中两位教师提到学生反馈会影响下一轮教学设计。"
        "研究团队对访谈内容进行了编码，并由两名成员交叉核验。"
    )

    segments = segment_document(text, Settings())

    assert len(segments) == 2
    assert segments[0].section_title == "第一章 绪论"
    assert segments[1].section_title == "第二章 方法"
    assert segments[1].paragraph_index == 2


def test_duplication_raw_score_is_clamped_to_non_negative() -> None:
    sections = [
        {
            "section_index": 0,
            "content": "“这是一个被完整引用的长句子，用来验证高引用占比时不会把原始查重分数扣成负数。”",
            "char_count": 40,
        }
    ]

    result = score_duplication(sections)

    assert len(result.section_scores) == 1
    assert result.section_scores[0].raw_score >= 0
    assert result.section_scores[0].normalized_score >= 0
