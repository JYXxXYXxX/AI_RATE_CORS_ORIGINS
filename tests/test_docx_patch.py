from __future__ import annotations

from io import BytesIO

from docx import Document

from app.services.docx_patch import export_docx_with_patches


def test_docx_patch_replaces_text_without_risk_shading(tmp_path) -> None:
    original = tmp_path / "original.docx"
    doc = Document()
    paragraph = doc.add_paragraph()
    paragraph.add_run("本文通过")
    paragraph.add_run("系统设计")
    paragraph.add_run("提升财务管理效率。")
    doc.save(original)

    blocks = [
        {
            "block_id": "b1",
            "block_type": "paragraph",
            "text": "本文通过系统设计提升财务管理效率。",
            "source_map": {"paragraphIndex": 0},
            "risk_score": 82,
        }
    ]
    patches = [
        {
            "block_id": "b1",
            "old_text": "本文通过系统设计提升财务管理效率。",
            "new_text": "本系统在预算提醒模块中读取收支记录，并据此生成财务提醒。",
        }
    ]

    output = export_docx_with_patches(str(original), blocks, patches)
    patched = Document(BytesIO(output))

    assert patched.paragraphs[0].text == "本系统在预算提醒模块中读取收支记录，并据此生成财务提醒。"
    p_pr_xml = patched.paragraphs[0]._element.get_or_add_pPr().xml
    assert "<w:shd" not in p_pr_xml


def test_docx_patch_can_optionally_export_highlighted_copy(tmp_path) -> None:
    original = tmp_path / "original.docx"
    doc = Document()
    doc.add_paragraph("这是一个高风险段落。")
    doc.save(original)

    output = export_docx_with_patches(
        str(original),
        [
            {
                "block_id": "b1",
                "block_type": "paragraph",
                "text": "这是一个高风险段落。",
                "source_map": {"paragraphIndex": 0},
                "risk_score": 82,
            }
        ],
        [],
        highlight_risks=True,
    )
    patched = Document(BytesIO(output))

    assert "<w:shd" in patched.paragraphs[0]._element.get_or_add_pPr().xml
