from __future__ import annotations

from io import BytesIO

from docx import Document

from app.models.domain import Article


def markdown(article: Article) -> str:
    return f"# {article.title}\n\n{article.body}\n\n---\n生成任务：{article.task_id}\n"


def plain_text(article: Article) -> str:
    return f"{article.title}\n\n{article.body}"


def word_document(article: Article) -> bytes:
    document = Document()
    document.add_heading(article.title, 0)
    for paragraph in article.body.split("\n"):
        if paragraph.strip():
            document.add_paragraph(paragraph.strip())
    output = BytesIO()
    document.save(output)
    return output.getvalue()
