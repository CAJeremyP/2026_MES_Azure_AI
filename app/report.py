"""
report.py — Generate an HTML results report (Session 5 output)
"""
from pathlib import Path
from datetime import datetime


def _escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_html_report(results: dict, output_path: Path):
    run_id     = results.get("run_id", "unknown")
    image_path = results.get("image_path", "")
    blob_url   = results.get("blob_url", "")
    vision     = results.get("vision", [])
    doc_intel  = results.get("document_intelligence", {})
    costs      = results.get("costs", {})

    vision_rows = ""
    for d in vision:
        bb = d.get("bounding_box", {})
        vision_rows += (
            f"<tr><td>{_escape(d['tag'])}</td>"
            f"<td class='pct'>{d['probability']:.1%}</td>"
            f"<td>{bb.get('left',0):.3f}</td><td>{bb.get('top',0):.3f}</td>"
            f"<td>{bb.get('width',0):.3f}</td><td>{bb.get('height',0):.3f}</td></tr>"
        )
    if not vision_rows:
        vision_rows = '<tr><td colspan="6" class="empty">No detections above threshold</td></tr>'

    ocr_rows = ""
    for i, line in enumerate(doc_intel.get("lines", []), 1):
        conf = f"{line['confidence']:.1%}" if line.get("confidence") else "n/a"
        ocr_rows += (
            f"<tr><td>{i}</td><td>{_escape(line['content'])}</td>"
            f"<td>{conf}</td><td>{line.get('page', 1)}</td></tr>"
        )
    if not ocr_rows:
        ocr_rows = '<tr><td colspan="4" class="empty">No text detected</td></tr>'

    cost_html = ""
    if "estimated" in costs:
        for svc, info in costs["estimated"].items():
            items = "".join(f"<li>{k.replace('_',' ').title()}: {_escape(str(v))}</li>" for k, v in info.items())
            cost_html += f"<div class='cost-item'><strong>{_escape(svc)}</strong><ul>{items}</ul></div>"
    elif "actual_costs" in costs:
        total    = costs.get("total", 0)
        currency = costs.get("currency", "USD")
        for item in costs["actual_costs"]:
            cost_html += f"<div class='cost-item'><strong>{_escape(item.get('service','Unknown'))}</strong>: ${float(item.get('cost',0)):.4f} {currency}</div>"
        cost_html += f"<div class='cost-total'>Total: ${total:.4f} {currency}</div>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Azure AI Demo &mdash; Results</title>
<style>
:root{{--azure:#0078d4;--azure-dark:#005a9e;--bg:#f3f6fb;--card:#fff;
      --text:#1a1a2e;--muted:#6b7280;--success:#107c10;--border:#dde3ed;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);}}
header{{background:linear-gradient(135deg,var(--azure-dark),var(--azure));color:#fff;padding:2rem 2.5rem;}}
header h1{{font-size:1.6rem;font-weight:600;}}
header .meta{{font-size:.85rem;opacity:.85;margin-top:.4rem;}}
main{{max-width:1100px;margin:0 auto;padding:2rem;}}
.card{{background:var(--card);border-radius:10px;border:1px solid var(--border);
       padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 1px 4px rgba(0,0,0,.05);}}
.card h2{{font-size:1rem;font-weight:600;color:var(--azure);margin-bottom:1rem;}}
.badge{{background:var(--azure);color:#fff;font-size:.7rem;padding:2px 8px;
        border-radius:20px;font-weight:500;margin-left:.4rem;}}
.blob-url{{font-size:.78rem;color:var(--muted);word-break:break-all;margin-bottom:.5rem;}}
table{{width:100%;border-collapse:collapse;font-size:.85rem;}}
th{{background:var(--bg);padding:.6rem .8rem;text-align:left;font-weight:600;
    color:var(--muted);border-bottom:2px solid var(--border);}}
td{{padding:.55rem .8rem;border-bottom:1px solid var(--border);vertical-align:top;}}
tr:last-child td{{border-bottom:none;}}
.pct{{font-weight:600;color:var(--success);}}
.empty{{color:var(--muted);font-style:italic;text-align:center;padding:1.5rem;}}
.cost-item{{margin-bottom:.8rem;}}
.cost-item ul{{margin-left:1.2rem;color:var(--muted);font-size:.85rem;}}
.cost-total{{font-weight:700;font-size:1rem;margin-top:1rem;color:var(--azure);}}
.tip{{background:#eff6ff;border-left:4px solid var(--azure);padding:.75rem 1rem;
      border-radius:0 6px 6px 0;font-size:.85rem;color:#1e40af;margin-top:1rem;}}
footer{{text-align:center;color:var(--muted);font-size:.78rem;padding:2rem;}}
</style>
</head>
<body>
<header>
  <h1>&#9889; Azure AI End-to-End Demo</h1>
  <div class="meta">Run: {run_id} &nbsp;&middot;&nbsp; {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} &nbsp;&middot;&nbsp; {Path(image_path).name}</div>
</header>
<main>
  <div class="card">
    <h2>&#128230; Input Image <span class="badge">Blob Storage</span></h2>
    <div class="blob-url">&#128279; {_escape(blob_url) or 'N/A'}</div>
    <div class="tip">Image uploaded to Azure Blob Storage (<strong>demo-images</strong> container). The blob URL is stored with every result row for full traceability.</div>
  </div>
  <div class="card">
    <h2>&#128310; Custom Vision &mdash; Shape Detection <span class="badge">{len(vision)} result(s)</span></h2>
    <table><tr><th>Tag</th><th>Confidence</th><th>Left</th><th>Top</th><th>Width</th><th>Height</th></tr>
    {vision_rows}</table>
  </div>
  <div class="card">
    <h2>&#128196; Document Intelligence &mdash; OCR <span class="badge">{len(doc_intel.get('lines',[]))} line(s)</span></h2>
    <table><tr><th>#</th><th>Text</th><th>Confidence</th><th>Page</th></tr>
    {ocr_rows}</table>
  </div>
  <div class="card">
    <h2>&#128176; Azure Cost Review</h2>
    {cost_html or '<p class="empty">Cost data unavailable &mdash; check Azure Portal</p>'}
    <div class="tip">All Cognitive Services use the <strong>F0 free tier</strong>. SQL is <strong>serverless</strong> and auto-pauses after 60 min idle. Run <code>teardown.sh</code> after the session to eliminate all charges.</div>
  </div>
</main>
<footer>Azure AI Demo &mdash; QA Learning Programme &nbsp;&middot;&nbsp; Sessions 4 &amp; 5</footer>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
