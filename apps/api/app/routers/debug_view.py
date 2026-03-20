"""
Debug view router  —  INTERNAL TOOLING ONLY
────────────────────────────────────────────
GET /debug
  Index of recent projects with trace presence and landing state summary.

GET /debug/project/{project_id}
  Full pipeline trace for one project, plus final saved landing state.

No JS. No CSS framework. No Jinja2. Inline HTML only.
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.debug_trace import PipelineTrace
from app.models.landing import LandingContent, LandingPage
from app.models.order import Project
from app.repositories.debug_trace_repo import DebugTraceRepository

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Stage constants ───────────────────────────────────────────────────────────
_STAGE_EXTRACTION = "extraction"
_STAGE_REPLY      = "reply_generation"
_STAGE_STEP1      = "landing_generation_step1"
_STAGE_STEP2      = "landing_generation_step2"
_STAGE_LABELS     = {
    _STAGE_EXTRACTION: "ext",
    _STAGE_REPLY:      "reply",
    _STAGE_STEP1:      "s1",
    _STAGE_STEP2:      "s2",
}

_INDEX_LIMIT = 50


# ─────────────────────────────────────────────────────────────────────────────
# Shared CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px; line-height: 1.5; color: #1a1a1a;
    background: #f5f5f5; padding: 24px;
  }
  h1 { font-size: 18px; font-weight: 600; margin-bottom: 4px; color: #111; }
  .meta { font-family: monospace; font-size: 12px; color: #666; margin-bottom: 24px; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .index-table { width: 100%; border-collapse: collapse; background: #fff;
    border: 1px solid #ddd; border-radius: 6px; overflow: hidden; }
  .index-table th { background: #f0f0f0; border-bottom: 1px solid #ddd;
    padding: 8px 12px; text-align: left; font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em; color: #555; }
  .index-table td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0;
    font-size: 13px; vertical-align: top; }
  .index-table tr:last-child td { border-bottom: none; }
  .index-table tr:hover td { background: #fafafa; }
  .mono-sm { font-family: monospace; font-size: 11px; color: #666; }
  .stage-dot { display: inline-block; width: 20px; text-align: center; }
  .dot-ok { color: #16a34a; font-weight: 700; }
  .dot-no { color: #d1d5db; }
  .status-public { color: #16a34a; font-size: 11px; font-weight: 600; }
  .status-draft { color: #9ca3af; font-size: 11px; }
  .summary-bar { background: #fff; border: 1px solid #ddd; border-radius: 6px;
    padding: 14px 16px; margin-bottom: 20px;
    display: flex; flex-wrap: wrap; gap: 16px; align-items: baseline; }
  .summary-item { font-size: 13px; color: #555; }
  .summary-item .key { font-weight: 600; color: #333; margin-right: 4px; }
  .summary-badge { display: inline-block; font-size: 11px; font-weight: 600;
    padding: 2px 7px; border-radius: 10px; vertical-align: middle; }
  .badge-public { background: #dcfce7; color: #15803d; }
  .badge-draft { background: #f3f4f6; color: #6b7280; }
  .section { background: #fff; border: 1px solid #ddd; border-radius: 6px;
    margin-bottom: 20px; overflow: hidden; }
  .section-header { background: #f0f0f0; border-bottom: 1px solid #ddd;
    padding: 10px 16px; font-weight: 600; font-size: 13px;
    text-transform: uppercase; letter-spacing: 0.05em; color: #444;
    display: flex; align-items: center; gap: 10px; }
  .section-note { font-size: 11px; font-weight: 400; text-transform: none;
    letter-spacing: 0; color: #888; }
  .section-warn { font-size: 11px; font-weight: 600; text-transform: none;
    letter-spacing: 0; color: #b45309; background: #fef3c7;
    padding: 2px 8px; border-radius: 10px; }
  .section-body { padding: 16px; }
  .fields { margin-bottom: 12px; }
  .kv { padding: 3px 0; border-bottom: 1px solid #f0f0f0; }
  .kv:last-child { border-bottom: none; }
  .key { font-weight: 600; color: #555; margin-right: 6px; }
  .null { color: #999; font-style: italic; }
  ul { margin: 4px 0 4px 20px; }
  li { padding: 1px 0; }
  .sub-section { font-size: 12px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; color: #888; margin: 14px 0 4px;
    padding-bottom: 3px; border-bottom: 1px solid #eee; }
  .raw-input { margin-bottom: 14px; }
  .field-label { font-weight: 600; color: #555; font-size: 12px; margin-bottom: 4px; }
  .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    font-size: 12px; background: #f8f8f8; border: 1px solid #e8e8e8;
    border-radius: 4px; padding: 10px; white-space: pre-wrap;
    word-break: break-word; max-height: 360px; overflow-y: auto; }
  .reply-block { border: 1px solid #e0e0e0; border-radius: 5px;
    padding: 12px; margin-bottom: 10px; background: #fafafa; }
  .reply-type { font-weight: 700; font-size: 13px; color: #333;
    margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
  .reply-text { margin-top: 6px; max-height: 200px; }
  details { margin-top: 10px; }
  .tech-summary { cursor: pointer; font-size: 12px; color: #888; padding: 4px 0; }
  .tech-summary:hover { color: #555; }
  details pre.mono { margin-top: 6px; }
  .photo-link { font-family: monospace; font-size: 12px; }
  .section.saved-section .section-header { background: #dbeafe; color: #1e40af; }
  .missing { color: #c0392b; font-style: italic; font-size: 13px; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# Shared HTML helpers
# ─────────────────────────────────────────────────────────────────────────────

def _esc(val) -> str:
    if val is None:
        return '<span class="null">null</span>'
    s = str(val)
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _parse(stored):
    if stored is None:
        return None
    try:
        return json.loads(stored)
    except Exception:
        return stored


def _kv(label: str, value) -> str:
    if value is None:
        return (f'<div class="kv"><span class="key">{_esc(label)}:</span> '
                f'<span class="null">null</span></div>')
    if isinstance(value, list):
        items = "".join(f"<li>{_esc(i)}</li>" for i in value) or "<li><em>[]</em></li>"
        return f'<div class="kv"><span class="key">{_esc(label)}:</span><ul>{items}</ul></div>'
    return f'<div class="kv"><span class="key">{_esc(label)}:</span> {_esc(value)}</div>'


def _collapsible(summary: str, content: str) -> str:
    return (
        f'<details><summary class="tech-summary">{_esc(summary)}</summary>'
        f'<pre class="mono">{content}</pre></details>'
    )


def _tech_details(record) -> str:
    ip = _parse(record.input_payload)
    return "\n".join([
        _collapsible("input_payload",
                     _esc(json.dumps(ip, ensure_ascii=False, indent=2) if ip is not None else "null")),
        _collapsible("prompt_text", _esc(record.prompt_text or "null")),
        _collapsible("raw_ai_output", _esc(record.raw_ai_output or "null")),
    ])


def _missing_stage(stage: str) -> str:
    return f'<p class="missing">No trace record for stage: {stage}</p>'


def _page_shell(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<style>{_CSS}</style>
</head>
<body>
{body}
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Index endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def debug_index(db: Session = Depends(get_db)):
    rows = (
        db.query(Project, LandingPage, LandingContent)
        .outerjoin(LandingPage, LandingPage.project_id == Project.id)
        .outerjoin(LandingContent, LandingContent.landing_page_id == LandingPage.id)
        .order_by(Project.created_at.desc())
        .limit(_INDEX_LIMIT)
        .all()
    )

    project_ids = [r[0].id for r in rows]
    stage_records = (
        db.query(PipelineTrace.project_id, PipelineTrace.stage)
        .filter(PipelineTrace.project_id.in_(project_ids))
        .distinct()
        .all()
    ) if project_ids else []

    stages_by_project: dict[str, set] = {}
    for pid, stage in stage_records:
        stages_by_project.setdefault(pid, set()).add(stage)

    return HTMLResponse(content=_render_index(rows, stages_by_project))


def _render_index(rows, stages_by_project: dict) -> str:
    if not rows:
        return _page_shell("Debug index",
                           "<h1>Debug index</h1><p style='margin-top:16px;color:#666'>No projects found.</p>")

    def _stage_dots(project_id: str) -> str:
        present = stages_by_project.get(project_id, set())
        return "".join(
            f'<span class="stage-dot dot-ok" title="{stage}">✓</span>'
            if stage in present else
            f'<span class="stage-dot dot-no" title="{stage}">·</span>'
            for stage in _STAGE_LABELS
        )

    def _status_cell(page) -> str:
        if page is None:
            return '<span class="null">—</span>'
        return ('<span class="status-public">public</span>' if page.is_public
                else f'<span class="status-draft">{_esc(page.status)}</span>')

    def _photo_cell(content) -> str:
        if content is None:
            return '<span class="null">—</span>'
        cj = content.content_json or {}
        sg = cj.get("style_grid") if isinstance(cj, dict) else None
        pid = sg.get("photo_set_id") if isinstance(sg, dict) else None
        if not pid:
            return '<span class="null">—</span>'
        return f'<span class="mono-sm" title="{_esc(pid)}">{_esc(pid[:8])}…</span>'

    thead = """<thead><tr>
  <th>created_at</th><th>project_id</th><th>title</th>
  <th>slug</th><th>status</th><th>photo_set_id</th>
  <th title="ext · reply · s1 · s2">stages</th><th></th>
</tr></thead>"""

    tbody = ""
    for project, page, content in rows:
        ts = project.created_at.strftime("%m-%d %H:%M") if project.created_at else "—"
        tbody += f"""<tr>
  <td class="mono-sm">{_esc(ts)}</td>
  <td class="mono-sm" title="{_esc(project.id)}">{_esc(project.id[:8])}…</td>
  <td>{_esc(project.title or "—")}</td>
  <td class="mono-sm">{_esc(page.slug if page else "—")}</td>
  <td>{_status_cell(page)}</td>
  <td>{_photo_cell(content)}</td>
  <td style="white-space:nowrap">{_stage_dots(project.id)}</td>
  <td><a href="/debug/project/{_esc(project.id)}">→ view</a></td>
</tr>"""

    legend = ('<div style="margin-top:10px;font-size:12px;color:#888">'
              'ext = extraction &nbsp;·&nbsp; reply = reply_generation '
              '&nbsp;·&nbsp; s1 = landing_step1 &nbsp;·&nbsp; s2 = landing_step2</div>')

    body = (f'<h1>Debug index</h1>'
            f'<div class="meta">showing last {_INDEX_LIMIT} projects · newest first</div>'
            f'<table class="index-table">{thead}<tbody>{tbody}</tbody></table>{legend}')
    return _page_shell("Debug index", body)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Per-project viewer (enhanced)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/project/{project_id}", response_class=HTMLResponse)
def debug_view(project_id: str, db: Session = Depends(get_db)):
    repo = DebugTraceRepository(db)
    all_records = repo.get_traces_by_project(project_id)
    latest: dict = {}
    for r in all_records:
        latest[r.stage] = r

    project = db.get(Project, project_id)
    page = (
        db.query(LandingPage)
        .options(joinedload(LandingPage.content))
        .filter(LandingPage.project_id == project_id)
        .first()
    )
    content = page.content if page else None

    return HTMLResponse(content=_render_project_page(project_id, project, page, content, latest))


def _render_summary_bar(project_id: str, project, page, content) -> str:
    title   = (project.title or "—") if project else "—"
    created = (project.created_at.strftime("%Y-%m-%d %H:%M UTC")
               if project and project.created_at else "—")
    slug    = page.slug if page else "—"

    if page is None:
        badge = '<span class="null">no landing</span>'
    elif page.is_public:
        badge = '<span class="summary-badge badge-public">public</span>'
    else:
        badge = f'<span class="summary-badge badge-draft">{_esc(page.status)}</span>'

    return (f'<div class="summary-bar">'
            f'<div class="summary-item"><span class="key">title:</span>{_esc(title)}</div>'
            f'<div class="summary-item"><span class="key">created:</span>{_esc(created)}</div>'
            f'<div class="summary-item"><span class="key">slug:</span>'
            f'<span class="mono-sm">{_esc(slug)}</span></div>'
            f'<div class="summary-item"><span class="key">status:</span>{badge}</div>'
            f'<div class="summary-item" style="margin-left:auto">'
            f'<a href="/debug" style="font-size:12px;color:#888">← index</a></div>'
            f'</div>')


def _render_saved_landing(page, content) -> str:
    if page is None:
        return '<p class="missing">No landing page saved for this project.</p>'
    if content is None:
        return '<p class="missing">Landing page exists but has no content.</p>'

    cj = content.content_json or {}
    if not isinstance(cj, dict):
        return '<p class="missing">content_json is not a valid object.</p>'

    sg = cj.get("style_grid")
    photo_set_id = sg.get("photo_set_id") if isinstance(sg, dict) else None
    if photo_set_id:
        photo_cell = (
            f'<span class="photo-link">{_esc(photo_set_id)}</span> '
            f'<a href="/public/photo-sets/{_esc(photo_set_id)}" target="_blank" '
            f'style="font-size:12px">→ /public/photo-sets/{_esc(photo_set_id[:8])}…</a>'
        )
    else:
        photo_cell = '<span class="null">null</span>'

    hero  = cj.get("hero")
    pc    = cj.get("price_card")
    cta   = cj.get("cta")

    rows  = _kv("slug",         cj.get("slug"))
    rows += _kv("template_key", cj.get("template_key"))
    rows += '<div class="sub-section">Style grid</div>'
    rows += f'<div class="kv"><span class="key">photo_set_id:</span> {photo_cell}</div>'
    rows += '<div class="sub-section">Hero</div>'
    rows += _kv("title",    hero.get("title")    if isinstance(hero, dict) else None)
    rows += _kv("subtitle", hero.get("subtitle") if isinstance(hero, dict) else None)
    rows += '<div class="sub-section">Price</div>'
    rows += _kv("price", pc.get("price") if isinstance(pc, dict) else None)
    rows += '<div class="sub-section">Quick questions</div>'
    rows += _kv("quick_questions", cj.get("quick_questions"))
    rows += '<div class="sub-section">CTA</div>'
    rows += _kv("channels", cta.get("channels") if isinstance(cta, dict) else None)
    rows += '<div class="sub-section">Optional blocks</div>'
    rows += _kv("badges",            cj.get("badges"))
    rows += _kv("photographer",      cj.get("photographer"))
    rows += _kv("personal_block",    cj.get("personal_block"))
    rows += _kv("reviews",           cj.get("reviews") or None)
    rows += _kv("secondary_actions", cj.get("secondary_actions") or None)

    full = _collapsible("full content_json",
                        _esc(json.dumps(cj, ensure_ascii=False, indent=2)))

    return f'<div class="fields">{rows}</div>\n{full}'


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
            "extracted_confidence", "client_intent_line", "situation_notes", "shoot_feel",
        ):
            rows += _kv(key, parsed.get(key))
    else:
        rows = '<p class="missing">parsed_output is null — validation failed</p>'

    ip = _parse(record.input_payload)
    raw_text = ip.get("raw_text", "") if isinstance(ip, dict) else ""
    return (f'<div class="raw-input"><div class="field-label">raw_text</div>'
            f'<pre class="mono">{_esc(raw_text)}</pre></div>'
            f'<div class="fields">{rows}</div>\n{_tech_details(record)}')


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
                blocks += (f'<div class="reply-block"><div class="reply-type">{label}</div>'
                           f'<p class="missing">missing</p></div>')
                continue
            blocks += (f'<div class="reply-block"><div class="reply-type">{label}</div>'
                       f'<div class="kv"><span class="key">preview:</span> {_esc(v.get("preview_text") or "")}</div>'
                       f'<div class="kv"><span class="key">message:</span></div>'
                       f'<pre class="mono reply-text">{_esc(v.get("message_text") or "")}</pre></div>')
    else:
        blocks = '<p class="missing">parsed_output is null — validation failed</p>'
    return f"{blocks}\n{_tech_details(record)}"


def _render_step1(record) -> str:
    if record is None:
        return _missing_stage(_STAGE_STEP1)
    parsed = _parse(record.parsed_output)
    rows = ""
    if isinstance(parsed, dict):
        rows += _kv("hero_subtitle",    parsed.get("hero_subtitle"))
        rows += _kv("work_steps",       parsed.get("work_steps"))
        rows += _kv("case_title",       parsed.get("case_title"))
        rows += _kv("case_description", parsed.get("case_description"))
        rows += _kv("hook_key",         parsed.get("hook_key"))
    else:
        rows = '<p class="missing">parsed_output is null — AI call failed</p>'

    ip = _parse(record.input_payload)
    return (f'<div class="fields">{rows}</div>\n'
            + _collapsible("input_payload",
                           _esc(json.dumps(ip, ensure_ascii=False, indent=2) if ip is not None else "null"))
            + "\n"
            + _collapsible("prompt_text", _esc(record.prompt_text or "null"))
            + "\n"
            + _collapsible("raw_ai_output (step 1 text)", _esc(record.raw_ai_output or "null")))


def _render_step2(record) -> str:
    if record is None:
        return _missing_stage(_STAGE_STEP2)
    parsed = _parse(record.parsed_output)
    rows = ""
    if isinstance(parsed, dict):
        rows += _kv("slug",         parsed.get("slug"))
        rows += _kv("template_key", parsed.get("template_key"))

        hero = parsed.get("hero")
        rows += '<div class="sub-section">Hero</div>'
        rows += _kv("title",    hero.get("title")    if isinstance(hero, dict) else None)
        rows += _kv("subtitle", hero.get("subtitle") if isinstance(hero, dict) else None)

        pc = parsed.get("price_card")
        rows += '<div class="sub-section">Price card</div>'
        rows += _kv("price",       pc.get("price")       if isinstance(pc, dict) else None)
        rows += _kv("description", pc.get("description") if isinstance(pc, dict) else None)

        sg = parsed.get("style_grid")
        rows += '<div class="sub-section">Style grid (pre-snapshot — may differ from saved landing)</div>'
        rows += _kv("photo_set_id", sg.get("photo_set_id") if isinstance(sg, dict) else None)

        wb = parsed.get("work_block")
        rows += '<div class="sub-section">Work block</div>'
        rows += _kv("steps", wb.get("steps") if isinstance(wb, dict) else None)

        sc = parsed.get("similar_case")
        rows += '<div class="sub-section">Similar case</div>'
        rows += _kv("title",       sc.get("title")       if isinstance(sc, dict) else None)
        rows += _kv("description", sc.get("description") if isinstance(sc, dict) else None)

        rows += '<div class="sub-section">Quick questions</div>'
        rows += _kv("quick_questions", parsed.get("quick_questions"))

        cta = parsed.get("cta")
        rows += '<div class="sub-section">CTA</div>'
        rows += _kv("channels", cta.get("channels") if isinstance(cta, dict) else None)

        rows += '<div class="sub-section">Optional blocks</div>'
        rows += _kv("badges",            parsed.get("badges"))
        rows += _kv("photographer",      parsed.get("photographer"))
        rows += _kv("personal_block",    parsed.get("personal_block"))
        rows += _kv("reviews",           parsed.get("reviews") or None)
        rows += _kv("secondary_actions", parsed.get("secondary_actions") or None)
    else:
        rows = '<p class="missing">parsed_output is null — validation failed after repair attempt</p>'
    return f'<div class="fields">{rows}</div>\n{_tech_details(record)}'


def _render_project_page(project_id: str, project, page, content, latest: dict) -> str:
    summary      = _render_summary_bar(project_id, project, page, content)
    saved_html   = _render_saved_landing(page, content)
    ext_html     = _render_extraction(latest.get(_STAGE_EXTRACTION))
    reply_html   = _render_reply(latest.get(_STAGE_REPLY))
    step1_html   = _render_step1(latest.get(_STAGE_STEP1))
    step2_html   = _render_step2(latest.get(_STAGE_STEP2))

    body = f"""
<h1>Pipeline debug trace</h1>
<div class="meta">project_id: {_esc(project_id)}</div>
{summary}
<div class="section saved-section">
  <div class="section-header">
    ★ Saved landing state
    <span class="section-note">final content_json from DB — post-snapshot</span>
  </div>
  <div class="section-body">{saved_html}</div>
</div>
<div class="section">
  <div class="section-header">1 — Extraction</div>
  <div class="section-body">{ext_html}</div>
</div>
<div class="section">
  <div class="section-header">2 — Reply generation</div>
  <div class="section-body">{reply_html}</div>
</div>
<div class="section">
  <div class="section-header">
    3 — Landing step 1
    <span class="section-note">(semantic draft)</span>
  </div>
  <div class="section-body">{step1_html}</div>
</div>
<div class="section">
  <div class="section-header">
    4 — Landing step 2
    <span class="section-note">(JSON model)</span>
    <span class="section-warn">⚠ pre-snapshot — photo_set_id may differ from saved landing</span>
  </div>
  <div class="section-body">{step2_html}</div>
</div>
"""
    return _page_shell(f"Debug: {project_id[:8]}…", body)
