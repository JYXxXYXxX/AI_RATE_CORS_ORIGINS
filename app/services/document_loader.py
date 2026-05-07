import re
from io import BytesIO

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".doc", ".pdf"}


def _check_magic_bytes(content: bytes, expected_ext: str) -> None:
    """基于文件头 magic bytes 校验文件类型，防止扩展名伪造。"""
    if expected_ext in (".txt", ".md"):
        return
    if expected_ext == ".pdf":
        if not content.startswith(b"%PDF"):
            raise ValueError("文件内容不是有效的 PDF 格式")
        return
    if expected_ext == ".docx":
        if not content.startswith(b"PK"):
            raise ValueError("文件内容不是有效的 DOCX 格式")
        return
    if expected_ext == ".doc":
        if not content.startswith(b"\xd0\xcf\x11\xe0"):
            raise ValueError("文件内容不是有效的 DOC 格式")
        return


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith((".txt", ".md")):
        _check_magic_bytes(content, ".txt")
        return _decode_text(content)
    if lower.endswith(".docx"):
        _check_magic_bytes(content, ".docx")
        return _extract_docx(content)
    if lower.endswith(".doc"):
        _check_magic_bytes(content, ".doc")
        return _extract_doc(content)
    if lower.endswith(".pdf"):
        _check_magic_bytes(content, ".pdf")
        return _extract_pdf(content)
    raise ValueError("仅支持 .txt、.md、.doc、.docx、.pdf 文件")


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _extract_docx(content: bytes) -> str:
    document = Document(BytesIO(content))
    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]
    return "\n\n".join(paragraphs)


def _extract_doc(content: bytes) -> str:
    """提取 .doc 格式文本。

    优先尝试 antiword，不可用时尝试 textract，
    最终降级为从二进制中提取可读文本。
    """
    # 方案 1: antiword (需要系统安装)
    try:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        result = subprocess.run(
            ["antiword", tmp_path],
            capture_output=True,
            timeout=30,
        )
        import os

        os.unlink(tmp_path)
        if result.returncode == 0:
            text = result.stdout.decode("utf-8", errors="ignore")
            if text.strip():
                return text
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # 方案 2: 从二进制中提取可读中文/英文文本（降级方案）
    text = _extract_text_from_binary(content)
    if len(text.strip()) >= 100:
        # 质量校验：中文比例过低说明提取失败（.doc 二进制中有大量非文本字符）
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text.strip())
        if total_chars > 0 and chinese_chars / total_chars >= 0.20:
            return text

    raise ValueError(
        ".doc 格式解析失败：无法提取有效文本。建议将文件另存为 .docx 格式后重新上传。"
    )


def _extract_text_from_binary(content: bytes) -> str:
    """从二进制文件中尽力提取可读文本（降级方案）。"""
    import re

    try:
        raw = content.decode("utf-8", errors="ignore")
    except Exception:
        raw = content.decode("gb18030", errors="ignore")
    # 提取连续的中文或英文文本片段
    chunks = re.findall(r"[\u4e00-\u9fff\w\s。，！？、；：" "''（）\[\]【】]{10,}", raw)
    return "\n".join(chunks)


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)
