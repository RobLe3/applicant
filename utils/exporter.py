import os
import re
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape


def render_template(template, context):
    text = template
    for key, value in context.items():
        placeholder = "{{" + key + "}}"
        text = text.replace(placeholder, value)
    return re.sub(r"{{\\w+}}", "", text)


def build_cover_letter_text(template, context):
    rendered = render_template(template, context)
    return rendered.strip() + "\n"


def _split_lines(text):
    return (text or "").splitlines()


def export_docx(text, path):
    lines = _split_lines(text)
    doc_xml = _docx_document_xml(lines)
    content_types = _docx_content_types()
    rels = _docx_rels()

    _write_docx(path, content_types, rels, doc_xml)


def _docx_content_types():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )


def _docx_rels():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )


def _docx_document_xml(lines):
    body_parts = []
    for line in lines:
        if not line.strip():
            body_parts.append("<w:p/>")
            continue
        escaped = escape(line)
        body_parts.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">"
            + escaped
            + "</w:t></w:r></w:p>"
        )
    body = "".join(body_parts)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + body
        + "</w:body></w:document>"
    )


def _write_docx(path, content_types, rels, doc_xml):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    timestamp = datetime(2000, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _write_zip_entry(zf, "[Content_Types].xml", content_types, timestamp)
        _write_zip_entry(zf, "_rels/.rels", rels, timestamp)
        _write_zip_entry(zf, "word/document.xml", doc_xml, timestamp)


def _write_zip_entry(zf, name, content, timestamp):
    info = zipfile.ZipInfo(name)
    info.date_time = (
        timestamp.year,
        timestamp.month,
        timestamp.day,
        timestamp.hour,
        timestamp.minute,
        timestamp.second,
    )
    zf.writestr(info, content)


def export_pdf(text, path):
    lines = _split_lines(text)
    stream = _pdf_text_stream(lines)
    pdf = _build_pdf(stream)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(pdf)


def _escape_pdf_text(text):
    return text.replace("\\\\", "\\\\\\\\").replace("(", "\\\\(").replace(")", "\\\\)")


def _pdf_text_stream(lines):
    parts = ["BT", "/F1 12 Tf", "72 720 Td"]
    first = True
    for line in lines:
        if not first:
            parts.append("0 -14 Td")
        first = False
        parts.append(f"({_escape_pdf_text(line)}) Tj")
    parts.append("ET")
    return "\n".join(parts)


def _build_pdf(stream):
    stream_bytes = stream.encode("latin-1", errors="replace")
    objects = []
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>\nendobj\n"
    )
    objects.append("4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(
        "5 0 obj\n<< /Length "
        + str(len(stream_bytes))
        + " >>\nstream\n"
        + stream
        + "\nendstream\nendobj\n"
    )

    offsets = []
    pdf = b"%PDF-1.4\n"
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj.encode("latin-1")
    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode("latin-1")
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")
    return pdf
