from app.services.cnki_ocr import extract_cnki_feedback_preview
from app.services.cnki_report_parser import parse_cnki_report_bytes


def test_ocr_preview_infers_duplication_from_self_write_rate() -> None:
    preview = extract_cnki_feedback_preview(
        "cnki.txt",
        "自写率 98.27% 去除引用本人文献相似率 1.73% 报告日期 2026-05-14".encode("utf-8"),
    )

    assert preview["cnki_dup_percent"] == 1.73
    assert preview["report_date"] == "2026-05-14"


def test_report_parser_infers_total_copy_ratio_from_self_write_rate() -> None:
    report = parse_cnki_report_bytes(
        "cnki-report.html",
        """
        <html>
          <body>
            <div>原文对照报告</div>
            <div>自写率：98.27%</div>
            <div>去除引用本人文献相似率：1.73%</div>
          </body>
        </html>
        """.encode("utf-8"),
    )

    assert report.report_type == "similarity"
    assert report.total_copy_ratio == 1.73
