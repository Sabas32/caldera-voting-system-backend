from __future__ import annotations

import base64
from html import escape
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency
    qrcode = None
from django.http import HttpResponse


def build_csv_response(filename: str, rows: list[dict[str, str]]) -> HttpResponse:
    sio = StringIO()
    sio.write("token,label,election_slug\n")
    for row in rows:
        sio.write(f"{row['token']},{row['label']},{row['election_slug']}\n")
    response = HttpResponse(sio.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def build_print_html(batch_label: str, election_slug: str, tokens: list[str]) -> str:
    cards = "".join(
        (
            "<div class='card'>"
            f"<p class='label'>{batch_label}</p>"
            f"<p class='token'>{token}</p>"
            f"<p class='path'>/e/{election_slug}</p>"
            "</div>"
        )
        for token in tokens
    )
    return f"""
<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>Token Sheet</title>
<style>
@page {{ size: A4; margin: 12mm; }}
* {{ box-sizing: border-box; }}
body {{
  font-family: Inter, Arial, sans-serif;
  margin: 0;
  color: #0b0f19;
}}
h1 {{
  margin: 0 0 12px;
  font-size: 18px;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}}
.card {{
  border: 1px solid #d9dde5;
  border-radius: 10px;
  padding: 10px;
  min-height: 86px;
  page-break-inside: avoid;
}}
.label {{
  margin: 0 0 6px;
  font-size: 12px;
  color: #5a6475;
}}
.token {{
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.08em;
}}
.path {{
  margin: 6px 0 0;
  font-size: 12px;
  color: #5a6475;
}}
</style>
</head>
<body>
<h1>Token Sheet - {batch_label}</h1>
<div class='grid'>{cards}</div>
</body>
</html>
"""


def build_qr_zip(tokens: list[str], election_slug: str) -> bytes:
    if qrcode is None:
        raise RuntimeError("QR export is unavailable because qrcode is not installed.")
    mem_file = BytesIO()
    with ZipFile(mem_file, "w", ZIP_DEFLATED) as zip_file:
        for token in tokens:
            img = qrcode.make(f"{token}")
            output = BytesIO()
            img.save(output, format="PNG")
            zip_file.writestr(f"{election_slug}_{token}.png", output.getvalue())
    mem_file.seek(0)
    return mem_file.read()


def build_qr_print_html(batch_label: str, election_slug: str, tokens: list[str]) -> str:
    if qrcode is None:
        raise RuntimeError("QR print preview is unavailable because qrcode is not installed.")

    cards = []
    for token in tokens:
        qr_image = qrcode.make(token)
        output = BytesIO()
        qr_image.save(output, format="PNG")
        encoded_qr = base64.b64encode(output.getvalue()).decode("ascii")
        cards.append(
            (
                "<div class='card'>"
                f"<img class='qr' src='data:image/png;base64,{encoded_qr}' alt='Token QR code' />"
                "<div class='meta'>"
                f"<p class='token'>{escape(token)}</p>"
                f"<p class='path'>/e/{escape(election_slug)}</p>"
                "</div>"
                "</div>"
            )
        )

    cards_markup = "".join(cards)
    return f"""
<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>QR Token Sheet</title>
<style>
@page {{ size: A4; margin: 10mm; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: Inter, Arial, sans-serif;
  color: #0b0f19;
}}
.header {{
  margin-bottom: 10px;
}}
.title {{
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}}
.subtitle {{
  margin: 4px 0 0;
  font-size: 12px;
  color: #5a6475;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}}
.card {{
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #d9dde5;
  border-radius: 10px;
  padding: 10px;
  min-height: 146px;
  page-break-inside: avoid;
  break-inside: avoid;
}}
.qr {{
  width: 120px;
  height: 120px;
  border-radius: 6px;
}}
.meta {{
  min-width: 0;
}}
.token {{
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
  word-break: break-all;
}}
.path {{
  margin: 6px 0 0;
  font-size: 12px;
  color: #5a6475;
}}
@media print {{
  body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
</style>
</head>
<body>
  <div class='header'>
    <h1 class='title'>QR Token Print Preview - {escape(batch_label)}</h1>
    <p class='subtitle'>Election path: /e/{escape(election_slug)} | Total tokens: {len(tokens)}</p>
  </div>
  <div class='grid'>{cards_markup}</div>
</body>
</html>
"""
