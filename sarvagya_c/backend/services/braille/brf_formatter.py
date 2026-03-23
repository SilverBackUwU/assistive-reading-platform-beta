from __future__ import annotations


def format_brf(text: str, line_width: int, page_height: int) -> str:
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        candidate = word if not current_line else f"{current_line} {word}"
        if len(candidate) <= line_width:
            current_line = candidate
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    pages: list[str] = []
    for index in range(0, len(lines), page_height):
        pages.append("\n".join(lines[index:index + page_height]))
    return "\f".join(pages)
