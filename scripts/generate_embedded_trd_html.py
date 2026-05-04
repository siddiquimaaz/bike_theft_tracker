import base64
import re
from pathlib import Path

import markdown


REPO_ROOT = Path(__file__).resolve().parents[1]
MD_PATH = REPO_ROOT / "docs" / "TRD.md"
OUT_PATH = REPO_ROOT / "docs" / "TRD_print_ready_embedded.html"


def mime_from_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def embed_markdown_images(md_text: str, md_base_dir: Path) -> str:
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def replacer(match: re.Match) -> str:
        alt = match.group(1)
        raw_src = match.group(2).strip()
        src = raw_src.split()[0]

        if src.startswith("http://") or src.startswith("https://") or src.startswith("data:"):
            return match.group(0)

        img_path = (md_base_dir / src).resolve()
        if not img_path.exists():
            return match.group(0)

        data = base64.b64encode(img_path.read_bytes()).decode("ascii")
        mime = mime_from_suffix(img_path)
        return f"![{alt}](data:{mime};base64,{data})"

    return pattern.sub(replacer, md_text)


def main() -> None:
    md_text = MD_PATH.read_text(encoding="utf-8")
    md_text = embed_markdown_images(md_text, MD_PATH.parent)

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "md_in_html"],
        output_format="html5",
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>TRD - Bike Theft Tracker</title>
  <style>
    body {{
      font-family: "Times New Roman", serif;
      line-height: 1.45;
      margin: 24px auto;
      max-width: 900px;
      color: #111;
      padding: 0 18px;
    }}
    h1, h2, h3, h4 {{
      margin-top: 1.2em;
      margin-bottom: 0.45em;
    }}
    p, li {{
      font-size: 12pt;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 12px 0;
      font-size: 11pt;
    }}
    th, td {{
      border: 1px solid #444;
      padding: 6px 8px;
      vertical-align: top;
    }}
    img {{
      max-width: 100%;
      height: auto;
      display: block;
      margin: 10px auto 16px;
      border: 1px solid #ddd;
    }}
    code {{
      white-space: pre-wrap;
      word-break: break-word;
    }}
    hr {{
      border: none;
      border-top: 1px solid #bbb;
      margin: 20px 0;
    }}
    @media print {{
      body {{
        max-width: none;
        margin: 0;
        padding: 8mm;
      }}
      img {{
        page-break-inside: avoid;
      }}
    }}
  </style>
</head>
<body>
{html_body}
</body>
</html>
"""

    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Generated: {OUT_PATH}")


if __name__ == "__main__":
    main()
