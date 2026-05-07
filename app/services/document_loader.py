import re
import subprocess
import tempfile
import os
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


def _run_external_tool(cmd: list[str], content: bytes, timeout: int = 60) -> str | None:
    """调用外部命令提取文本，失败返回 None。"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        result = subprocess.run(
            cmd + [tmp_path],
            capture_output=True,
            timeout=timeout,
        )
        os.unlink(tmp_path)
        if result.returncode == 0:
            text = result.stdout.decode("utf-8", errors="ignore")
            if text.strip():
                return text
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, subprocess.CalledProcessError):
        pass
    return None


def _extract_doc(content: bytes) -> str:
    """提取 .doc 格式文本。

    尝试顺序：
    1. antiword（解析质量最好）
    2. catdoc（备选工具）
    3. strings（从二进制提取可读字符串）
    4. 纯 Python 正则提取（最终降级）
    """
    # 方案 1: antiword
    text = _run_external_tool(["antiword"], content, timeout=60)
    if text:
        return text

    # 方案 2: catdoc
    text = _run_external_tool(["catdoc"], content, timeout=60)
    if text:
        return text

    # 方案 3: strings（从二进制提取可读字符串）
    text = _run_external_tool(["strings", "-e", "l"], content, timeout=60)
    if text and len(text.strip()) >= 200:
        if _is_acceptable_quality(text):
            return text

    # 方案 4: Python 正则提取
    text = _extract_text_from_binary(content)
    if _is_acceptable_quality(text):
        return text

    raise ValueError(
        ".doc 格式解析失败：无法提取有效文本。建议将文件另存为 .docx 格式后重新上传。"
    )


def _is_acceptable_quality(text: str) -> bool:
    """判断提取的文本质量是否可接受。"""
    stripped = text.strip()
    if not stripped:
        return False

    total_chars = len(stripped)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", stripped))

    # 中文文档：只要有足够中文字符就接受
    if chinese_chars >= 100:
        return True

    # 中英混合/英文文档：总长度足够且有中文迹象，或纯英文长度很长
    if total_chars >= 500 and chinese_chars >= 20:
        return True
    if total_chars >= 1000 and chinese_chars >= 5:
        return True

    return False


def _extract_text_from_binary(content: bytes) -> str:
    """从二进制文件中尽力提取可读文本（降级方案）。"""
    # .doc 文件内部常用 UTF-16LE 或 ANSI 编码存储文本
    candidates = []

    # 尝试 UTF-16LE 解码（.doc 内部文本常见格式）
    try:
        candidates.append(content.decode("utf-16le", errors="ignore"))
    except Exception:
        pass

    # 尝试 gb18030（中文文档常见编码）
    try:
        candidates.append(content.decode("gb18030", errors="ignore"))
    except Exception:
        pass

    # 通用 UTF-8 降级
    try:
        candidates.append(content.decode("utf-8", errors="ignore"))
    except Exception:
        pass

    # 选择中文字符最多的解码结果
    best = ""
    best_score = 0
    for raw in candidates:
        score = len(re.findall(r"[\u4e00-\u9fff]", raw))
        if score > best_score:
            best_score = score
            best = raw

    if not best:
        best = content.decode("utf-8", errors="ignore")

    # 提取连续的可读文本片段（中文、英文、数字、常见标点）
    pattern = r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\w\s。，！？、；：'\"''（）\[\]【】]{10,}"
    chunks = re.findall(pattern, best)
    return "\n".join(chunks)


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)
