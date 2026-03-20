"""
Debug view router  —  INTERNAL TOOLING ONLY
────────────────────────────────────────────
GET /debug/project/{project_id}

Returns a browser-readable HTML page showing the full AI pipeline trace
for a project.

Renders 4 sections:
  1. Extraction
  2. Reply generation  (SHORT / WARM / EXPERT)
  3. Landing step 1    (semantic draft)
  4. Landing step 2    (LandingPageModel fields)

Technical details (input_payload, prompt_text, raw_ai_output) are
collapsed by default via <details><summary>.

Shows the LATEST trace record per stage — for full history use
GET /projects/{project_id}/debug-trace (JSON endpoint).

No JS. No CSS framework. No Jinja2. Inline HTML only.
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.debug_trace_repo import DebugTraceRepository

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Stage name constants (must match values written by services) ──────────
_STAGE_EXTRACTION   = "extraction"
_STAGE_REPLY        = "reply_generation"
_STAGE_STEP1        = "landing_generation_step1"
_STAGE_STEP2        = "landing_generation_step2"


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/project/{project_id}", response_class=HTMLResponse)
def debug_view(project_id: str, db: Session = Depends(get_db)):
    repo = DebugTraceRepository(db)
    all_records = repo.get_traces_by_project(project_id)

    # Keep latest record per stage (records are sorted ASC — last wins)
    latest: dict[str, object] = {}
    for r in all_records:
        latest[r.stage] = r

    html = _render_page(project_id, latest)
    return HTMLResponse(content=html)


# ─────────────────────────────────────────────────────────────────────────────
# HTML helpers
# ─────────────────────────────────────────────────────────────────────────────

def _esc(val) -> str:
    """HTML-escape a value for safe inline display."""
    if val is None:
        return '<span class="null">null</span>'
    s = str(val)
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _parse(stored: str | None):
    """Parse stored JSON string → Python object, or return raw string."""
    if stored is None:
        return None
    try:
        return json.loads(stored)
    except Exception:
        return stored


def _kv(label: str, value) -> str:
    """Render a single key-value row."""
    if value is None:
        return f'<div class="kv"><span class="key">{_esc(label)}:</span> <span class="null">null</span></div>'
    if isinstance(value, list):
        items = "".join(f"<li>{_esc(i)}</li>" for i in value) or "<li><em>[]</em></li>"
        return f'<div class="kv"><span class="key">{_esc(label)}:</span><ul>{items}</ul></div>'
    return f'<div class="kv"><span class="key">{_esc(label)}:</span> {_esc(value)}</div>'


def _collapsible(summary: str, content: str) -> str:
    """Wrap content in a collapsed <details> block."""
    return (
        f'<details><summary class="tech-summary">{_esc(summary)}</summary>'
        f'<pre class="mono">{content}</pre></details>'
    )


def _tech_details(record) -> str:
    """Render collapsed technical details block for any stage."""
    parts = []
    ip = _parse(record.input_payload)
    parts.append(_collapsible(
        "input_payload",
        _esc(json.dumps(ip, ensure_ascii=False, indent=2) if ip is not None else "null"),
    ))
    parts.append(_collapsible(
        "prompt_text",
        _esc(record.prompt_text or "null"),
    ))
    parts.append(_collapsible(
        "raw_ai_output",
        _esc(record.raw_ai_output or "null"),
    ))
    return "\n".join(parts)


def _missing_stage(stage: str) -> str:
    return f'<p class="missing">No trace record for stage: {stage}</p>'


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_extraction(record) -> str:
    if record is None:
        return _missing_stage(_STAGE_EXTRACTION)

    parsed = _parse(record.parsed_output)
    rows = ""
    if isinstance(parsed, dict):
        for key in (
            "client_name", "client_label", "event_type", "event_subtype",
            "city", "location", "event_date", "date_text", "duration_text",
            "guest_count_text", "budget_max", "currency",
            "requirements", "priority_signals", "tone_signal",
            "extracted_confidence",
            "client_intent_line", "situation_notes", "shoot_feel",
        ):
            rows += _kv(key, parsed.get(key))
    else:
        rows = '<p class="missing">parsed_output is null — validation failed</p>'

    ip = _parse(record.input_payload)
    raw_text = ""
    if isinstance(ip, dict):
        raw_text = ip.get("raw_text", "")

    return f"""
<div class="raw-input">
  <div class="field-label">raw_text</div>
  <pre class="mono">{_esc(raw_text)}</pre>
</div>
<div class="fields">{rows}</div>
{_tech_details(record)}
"""


def _render_reply(record) -> str:
    if record is None:
        return _missing_stage(_STAGE_REPLY)

    parsed = _parse(record.parsed_output)
    blocks = ""

    if isinstance(parsed, list):
        by_type = {v.get("variant_type"): v for v in parsed if isinstance(v, dict)}
        for vtype in ("short", "warm", "expert"):
            v = by_type.get(vtype)
            label = vtype.upper()
            if v is None:
                blocks += f'<div class="reply-block"><div class="reply-type">{label}</div><p class="missing">missing</p></div>'
                continue
            preview = _esc(v.get("preview_text") or "")
            message = _esc(v.get("message_text") or "")
            blocks += f"""
<div class="reply-block">
  <div class="reply-type">{label}</div>
  <div class="kv"><span class="key">preview:</span> {preview}</div>
  <div class="kv"><span class="key">message:</span></div>
  <pre class="mono reply-text">{message}</pre>
</div>"""
    else:
        blocks = '<p class="missing">parsed_output is null — validation failed</p>'

    return f"{blocks}\n{_tech_details(record)}"


def _render_step1(record) -> str:
    if record is None:
        return _missing_stage(_STAGE_STEP1)

    parsed = _parse(record.parsed_output)
    rows = ""

    if isinstance(parsed, dict):
        rows += _kv("hero_subtitle", parsed.get("hero_subtitle"))
        rows += _kv("work_steps",    parsed.get("work_steps"))
        rows += _kv("case_title",    parsed.get("case_title"))
        rows += _kv("case_description", parsed.get("case_description"))
        rows += _kv("hook_key",      parsed.get("hook_key"))
    else:
        rows = '<p class="missing">parsed_output is null — AI call failed</p>'

    # raw step1 output is plain text, not JSON — show it directly
    raw_text = record.raw_ai_output or ""
    raw_block = _collapsible("raw_ai_output (step 1 text)", _esc(raw_text))

    ip = _parse(record.input_payload)
    ip_block = _collapsible(
        "input_payload",
        _esc(json.dumps(ip, ensure_ascii=False, indent=2) if ip is not None else "null"),
    )
    prompt_block = _collapsible("prompt_text", _esc(record.prompt_text or "null"))

    return f'<div class="fields">{rows}</div>\n{ip_block}\n{prompt_block}\n{raw_block}'


def _render_step2(record) -> str:
    if record is None:
        return _missing_stage(_STAGE_STEP2)

    parsed = _parse(record.parsed_output)
    rows = ""

    if isinstance(parsed, dict):
        # slug / template
        rows += _kv("slug",         parsed.get("slug"))
        rows += _kv("template_key", parsed.get("template_key"))

        # hero
        hero = parsed.get("hero")
        rows += '<div class="sub-section">Hero</div>'
        if isinstance(hero, dict):
            rows += _kv("title",    hero.get("title"))
            rows += _kv("subtitle", hero.get("subtitle"))
        else:
            rows += _kv("hero", None)

        # price_card
        price = parsed.get("price_card")
        rows += '<div class="sub-section">Price card</div>'
        if isinstance(price, dict):
            rows += _kv("price",       price.get("price"))
            rows += _kv("description", price.get("description"))
        else:
            rows += _kv("price_card", None)

        # style_grid
        sg = parsed.get("style_grid")
        rows += '<div class="sub-section">Style grid</div>'
        rows += _kv("photo_set_id", sg.get("photo_set_id") if isinstance(sg, dict) else None)

        # work_block
        wb = parsed.get("work_block")
        rows += '<div class="sub-section">Work block</div>'
        if isinstance(wb, dict):
            rows += _kv("steps", wb.get("steps"))
        else:
            rows += _kv("work_block", None)

        # similar_case
        sc = parsed.get("similar_case")
        rows += '<div class="sub-section">Similar case</div>'
        if isinstance(sc, dict):
            rows += _kv("title",       sc.get("title"))
            rows += _kv("description", sc.get("description"))
        else:
            rows += _kv("similar_case", None)

        # quick_questions
        rows += '<div class="sub-section">Quick questions</div>'
        rows += _kv("quick_questions", parsed.get("quick_questions"))

        # cta
        cta = parsed.get("cta")
        rows += '<div class="sub-section">CTA</div>'
        rows += _kv("channels", cta.get("channels") if isinstance(cta, dict) else None)

        # optional blocks — always show, null if absent
        rows += '<div class="sub-section">Optional blocks</div>'
        rows += _kv("badges",         parsed.get("badges"))
        rows += _kv("photographer",   parsed.get("photographer"))
        rows += _kv("personal_block", parsed.get("personal_block"))
        rows += _kv("reviews",        parsed.get("reviews") or None)
        rows += _kv("secondary_actions", parsed.get("secondary_actions") or None)

    else:
        rows = '<p class="missing">parsed_output is null — validation failed after repair attempt</p>'

    return f'<div class="fields">{rows}</div>\n{_tech_details(record)}'


# ─────────────────────────────────────────────────────────────────────────────
# Page assembler
# ─────────────────────────────────────────────────────────────────────────────

def _render_page(project_id: str, latest: dict) -> str:
    extraction_html = _render_extraction(latest.get(_STAGE_EXTRACTION))
    reply_html      = _render_reply(latest.get(_STAGE_REPLY))
    step1_html      = _render_step1(latest.get(_STAGE_STEP1))
    step2_html      = _render_step2(latest.get(_STAGE_STEP2))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Debug: {_esc(project_id)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
    line-height: 1.5;
    color: #1a1a1a;
    background: #f5f5f5;
    padding: 24px;
  }}
  h1 {{
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
    color: #111;
  }}
  .project-id {{
    font-family: monospace;
    font-size: 12px;
    color: #666;
    margin-bottom: 28px;
  }}
  .section {{
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    margin-bottom: 20px;
    overflow: hidden;
  }}
  .section-header {{
    background: #f0f0f0;
    border-bottom: 1px solid #ddd;
    padding: 10px 16px;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #444;
  }}
  .section-body {{
    padding: 16px;
  }}
  .fields {{
    margin-bottom: 12px;
  }}
  .kv {{
    padding: 3px 0;
    border-bottom: 1px solid #f0f0f0;
  }}
  .kv:last-child {{ border-bottom: none; }}
  .key {{
    font-weight: 600;
    color: #555;
    margin-right: 6px;
  }}
  .null {{
    color: #999;
    font-style: italic;
  }}
  ul {{
    margin: 4px 0 4px 20px;
  }}
  li {{ padding: 1px 0; }}
  .sub-section {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    margin: 14px 0 4px;
    padding-bottom: 3px;
    border-bottom: 1px solid #eee;
  }}
  .raw-input {{
    margin-bottom: 14px;
  }}
  .field-label {{
    font-weight: 600;
    color: #555;
    font-size: 12px;
    margin-bottom: 4px;
  }}
  .mono {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    font-size: 12px;
    background: #f8f8f8;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    padding: 10px;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 360px;
    overflow-y: auto;
  }}
  .reply-block {{
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 12px;
    margin-bottom: 10px;
    background: #fafafa;
  }}
  .reply-type {{
    font-weight: 700;
    font-size: 13px;
    color: #333;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .reply-text {{
    margin-top: 6px;
    max-height: 200px;
  }}
  details {{
    margin-top: 10px;
  }}
  .tech-summary {{
    cursor: pointer;
    font-size: 12px;
    color: #888;
    padding: 4px 0;
    user-select: none;
  }}
  .tech-summary:hover {{ color: #555; }}
  details pre.mono {{ margin-top: 6px; }}
  .missing {{
    color: #c0392b;
    font-style: italic;
    font-size: 13px;
  }}
</style>
</head>
<body>

<h1>Pipeline debug trace</h1>
<div class="project-id">project_id: {_esc(project_id)}</div>

<div class="section">
  <div class="section-header">1 — Extraction</div>
  <div class="section-body">{extraction_html}</div>
</div>

<div class="section">
  <div class="section-header">2 — Reply generation</div>
  <div class="section-body">{reply_html}</div>
</div>

<div class="section">
  <div class="section-header">3 — Landing step 1 &nbsp;<small style="font-weight:400;text-transform:none">(semantic draft)</small></div>
  <div class="section-body">{step1_html}</div>
</div>

<div class="section">
  <div class="section-header">4 — Landing step 2 &nbsp;<small style="font-weight:400;text-transform:none">(JSON model)</small></div>
  <div class="section-body">{step2_html}</div>
</div>

</body>
</html>"""
