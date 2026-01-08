import os
import re
import subprocess
import zipfile


class Document:
    def __init__(self, path, content, file_type, status, notes):
        self.path = path
        self.content = content
        self.file_type = file_type
        self.status = status
        self.notes = notes


def _docx_to_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_to_text(path):
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip(), "pypdf"
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["pdftotext", path, "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        if result.stdout:
            return result.stdout.strip(), "pdftotext"
    except Exception:
        pass

    return "", "unavailable"


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def _safe_name(path):
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", path)


def load_documents(folder_path, output_text_dir=None):
    documents = []
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.startswith("."):
                continue
            path = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()
            content = ""
            status = "skipped"
            notes = ""

            if ext in {".txt", ".md"}:
                content = _read_text(path)
                status = "ok"
            elif ext == ".docx":
                try:
                    content = _docx_to_text(path)
                    status = "ok"
                except Exception as exc:
                    notes = f"docx parse failed: {exc}"
            elif ext == ".pdf":
                content, method = _pdf_to_text(path)
                if content:
                    status = "ok"
                    notes = f"pdf parsed via {method}"
                else:
                    notes = "pdf parsing unavailable"
            else:
                notes = "unsupported file type"

            if output_text_dir and content:
                os.makedirs(output_text_dir, exist_ok=True)
                out_name = _safe_name(os.path.relpath(path, folder_path)) + ".txt"
                out_path = os.path.join(output_text_dir, out_name)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)

            documents.append(Document(path, content, ext.lstrip("."), status, notes))

    return documents


def build_inventory(documents):
    inventory = []
    for doc in documents:
        inventory.append(
            {
                "path": doc.path,
                "file_type": doc.file_type,
                "status": doc.status,
                "notes": doc.notes,
                "char_count": len(doc.content or ""),
            }
        )
    return inventory
