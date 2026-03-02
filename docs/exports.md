# Exports

Token batch exports:
- CSV (`/export/csv/`)
- Print HTML A4 (`/export/print/`)
- QR ZIP (`/export/qr/`) when `qrcode` dependency is installed
- QR Print Preview HTML A4 (`/export/qr-print/`) when `qrcode` dependency is installed

Security behavior:
- plaintext tokens are returned only at generation time and cached temporarily
- database persists only token hashes
- when plaintext cache expires, export endpoints return `410 Gone`

Excel results export (`openpyxl`):
- Summary sheet: election metadata + turnout metrics
- One sheet per post: candidate votes and percentages
- Formatting:
  - bold header row
  - thin borders
  - freeze first row
  - auto-fit columns (bounded max width)
