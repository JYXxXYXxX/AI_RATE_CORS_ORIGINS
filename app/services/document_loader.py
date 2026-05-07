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
    2. catdoc（备选外部工具）
    3. olefile 读取 WordDocument 流 + 多编码解码
    4. 对整个文件内容多编码解码 + 可打印文本提取
    5. 返回最佳候选（确保不会完全失败）
    """
    # 方案 1: antiword
    text = _run_external_tool(["antiword"], content, timeout=60)
    if text:
        return text

    # 方案 2: catdoc
    text = _run_external_tool(["catdoc"], content, timeout=60)
    if text:
        return text

    # 方案 3: 通过 olefile 读取 WordDocument 流
    candidates: list[tuple[str, int, int]] = []
    ole_data = _read_ole_worddocument_stream(content)
    if ole_data:
        candidates.extend(_decode_with_encodings(ole_data))

    # 方案 4: 对整个文件内容尝试解码（覆盖 olefile 失败的情况）
    candidates.extend(_decode_with_encodings(content))

    # 选择最佳结果：优先中文字符多，其次总长度长
    if candidates:
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        best_text, chinese_count, total_len = candidates[0]

        # 如果中文足够多，直接返回
        if chinese_count >= 50:
            return best_text

        # 如果有一定长度的可读文本，也返回（避免完全失败）
        if total_len >= 200:
            return best_text

    # 最终兜底：如果上述都失败，返回一个尽力提取的结果
    fallback = _aggressive_text_extract(content)
    if fallback and len(fallback.strip()) >= 50:
        return fallback

    raise ValueError(
        ".doc 格式解析失败：无法提取有效文本。建议将文件另存为 .docx 格式后重新上传。"
    )


def _read_ole_worddocument_stream(content: bytes) -> bytes | None:
    """使用 olefile 读取 .doc 文件中的 WordDocument 流。"""
    try:
        import olefile
        ole = olefile.OleFileIO(BytesIO(content))
        if ole.exists("WordDocument"):
            return ole.openstream("WordDocument").read()
    except Exception:
        pass
    return None


def _decode_with_encodings(data: bytes) -> list[tuple[str, int, int]]:
    """对原始字节尝试多种编码解码，返回 (文本, 中文字符数, 总长度) 列表。"""
    candidates: list[tuple[str, int, int]] = []

    for encoding in ("utf-16le", "gb18030", "gbk", "latin-1", "cp1252", "utf-8"):
        try:
            decoded = data.decode(encoding, errors="ignore")
            cleaned = _clean_decoded_text(decoded)
            if len(cleaned.strip()) >= 50:
                chinese = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
                candidates.append((cleaned, chinese, len(cleaned.strip())))
        except Exception:
            continue

    return candidates


def _clean_decoded_text(text: str) -> str:
    """清理解码后的文本：移除控制字符，提取连续可读片段。"""
    # 保留可打印字符和常见空白
    cleaned = "".join(
        c for c in text if c.isprintable() or c in "\n\r\t"
    )

    # 提取连续的中文、英文、数字、常见标点片段
    pattern = r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\w\s。，！？、；：'\"''（）\[\]【】《》（）——…~·\|\-\–\—]{8,}"
    chunks = re.findall(pattern, cleaned)

    if not chunks:
        return cleaned

    return "\n".join(chunks)


def _aggressive_text_extract(content: bytes) -> str:
    """最终兜底方案：从二进制中暴力提取所有可能的文本。"""
    all_texts = []

    # 尝试 UTF-16LE（每隔 2 字节可能是中文）
    try:
        utf16 = content.decode("utf-16le", errors="ignore")
        cleaned = _clean_decoded_text(utf16)
        if cleaned.strip():
            all_texts.append(cleaned)
    except Exception:
        pass

    # 尝试 GB18030
    try:
        gb = content.decode("gb18030", errors="ignore")
        cleaned = _clean_decoded_text(gb)
        if cleaned.strip():
            all_texts.append(cleaned)
    except Exception:
        pass

    # 尝试 latin-1（不会失败，因为 latin-1 覆盖所有 256 个字节）
    try:
        latin = content.decode("latin-1", errors="ignore")
        cleaned = _clean_decoded_text(latin)
        if cleaned.strip():
            all_texts.append(cleaned)
    except Exception:
        pass

    if not all_texts:
        return ""

    # 选择中文字符最多的结果
    best = ""
    best_chinese = 0
    for text in all_texts:
        chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
        if chinese > best_chinese or (chinese == best_chinese and len(text) > len(best)):
            best_chinese = chinese
            best = text

    return best


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)
