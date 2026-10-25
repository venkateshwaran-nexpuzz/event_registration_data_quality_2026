# G11 Tech Titans — DataWise local web app

## Run in Antigravity on Windows
1. Extract the ZIP.
2. Open the extracted `G11_Tech_Titans_Local_Web_App` folder in Antigravity IDE.
3. Open Terminal and run `py server.py`.
4. Open **http://127.0.0.1:8000** in Chrome or Edge.
5. Click **Run analysis**. Use **Upload CSV** to process another file.
6. Stop the server with `Ctrl+C` in the terminal.

No npm, Node.js, Flask, or third-party Python packages are needed.

CSV must contain: `registration_id, person_id, full_name, email, phone, event_name`.

Outputs: `outputs/clean_records.csv`, `outputs/review_list.csv`, `outputs/invalid_records.csv`, and `outputs/summary.json`.

The app is local-only and binds to 127.0.0.1. Similar names and repeated identifiers are review signals, not proof of duplicate identity. Review flagged rows manually.
