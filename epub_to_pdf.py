#!/usr/bin/env python3
"""Convert EPUB files to PDF."""

import argparse
import sys
import tempfile
from pathlib import Path

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from weasyprint import HTML


def extract_html_from_epub(epub_path: str) -> str:
    """Read an EPUB file and return combined HTML content."""
    book = epub.read_epub(epub_path, options={"ignore_ncx": True})

    # Extract title and language for the HTML wrapper
    title = book.get_metadata("DC", "title")
    title = title[0][0] if title else "Untitled"

    # Collect CSS stylesheets embedded in the EPUB
    stylesheets = []
    for item in book.get_items_of_type(ebooklib.ITEM_STYLE):
        css = item.get_content().decode("utf-8", errors="replace")
        stylesheets.append(css)

    # Collect HTML content from document items in spine order
    spine_ids = [item_id for item_id, _ in book.spine]
    id_to_item = {item.get_id(): item for item in book.get_items()}

    body_parts = []
    for item_id in spine_ids:
        item = id_to_item.get(item_id)
        if item is None:
            continue
        html = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        if body:
            body_parts.append(body.decode_contents())
        else:
            body_parts.append(soup.decode_contents())

    combined_css = "\n".join(
        f"<style>{css}</style>" for css in stylesheets
    )

    combined_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    {combined_css}
    <style>
        body {{
            font-family: serif;
            line-height: 1.6;
            margin: 2cm;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>
<body>
    {"<hr>".join(body_parts)}
</body>
</html>"""

    return combined_html


def convert_epub_to_pdf(epub_path: str, pdf_path: str) -> None:
    """Convert an EPUB file to PDF and write it to pdf_path."""
    html_content = extract_html_from_epub(epub_path)
    HTML(string=html_content).write_pdf(pdf_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert EPUB files to PDF."
    )
    parser.add_argument("input", help="Path to the input EPUB file")
    parser.add_argument(
        "-o", "--output",
        help="Path for the output PDF file (default: same name with .pdf extension)",
    )
    args = parser.parse_args()

    epub_path = Path(args.input)
    if not epub_path.exists():
        print(f"Error: file not found: {epub_path}", file=sys.stderr)
        sys.exit(1)
    if not epub_path.suffix.lower() == ".epub":
        print(f"Warning: input file does not have .epub extension", file=sys.stderr)

    if args.output:
        pdf_path = Path(args.output)
    else:
        pdf_path = epub_path.with_suffix(".pdf")

    print(f"Converting: {epub_path} -> {pdf_path}")
    try:
        convert_epub_to_pdf(str(epub_path), str(pdf_path))
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. Output saved to {pdf_path}")


if __name__ == "__main__":
    main()
