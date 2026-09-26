#!/usr/bin/env python3
"""Render Samreena Jamshed's LinkedIn visuals from a JSON spec.

Usage:  python3 render.py spec.json OUT_DIR
Spec types:
  {"type":"infographic","layout":"flow"|"compare"|"stat", ...}  -> OUT_DIR/infographic.png (1080x1350)
  {"type":"carousel","slides":[...]}                              -> OUT_DIR/slide-NN.png + carousel.pdf
Optional "palette": one of PALETTES or "random"; default rotates daily.
See SKILL.md for the full field list.
"""
import json, sys, os, html
from playwright.sync_api import sync_playwright

W, H = 1080, 1350
HANDLE = "Samreena Jamshed"
ROLE = "AI Engineer · Data &amp; AI Solutions Architect"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px}
body{font-family:Inter,'Segoe UI','Liberation Sans',Arial,sans-serif;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased}
.page{width:1080px;height:1350px;padding:72px 72px 0 72px;display:flex;flex-direction:column;position:relative;overflow:hidden;background:var(--bg)}
.page:after{content:'';position:absolute;right:-180px;top:-180px;width:520px;height:520px;border-radius:50%;background:radial-gradient(circle,var(--soft) 0%,transparent 70%);opacity:.9;pointer-events:none}
.page.dark{background:linear-gradient(145deg,var(--dark) 0%,var(--dark2) 100%);color:#fff}
.page.dark:after{background:radial-gradient(circle,var(--accent) 0%,transparent 68%);opacity:.22}
.page > *{position:relative;z-index:1}
.page.dark .muted{color:rgba(255,255,255,.72)}
.kicker{font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:22px;font-weight:700;letter-spacing:2px;color:var(--accentText);text-transform:uppercase;margin-bottom:22px}
.page.dark .kicker{color:var(--onDark)}
h1{font-size:64px;line-height:1.08;font-weight:900;letter-spacing:-1.5px}
h1 em{font-style:normal;color:var(--accentText)}
.page.dark h1 em{color:var(--onDark)}
.sub{font-size:28px;line-height:1.4;color:var(--muted);margin-top:22px;font-weight:500}
.muted{color:var(--muted)}
.content{flex:1;display:flex;flex-direction:column;justify-content:center;padding:36px 0}
.footer{height:110px;border-top:2px solid var(--line);display:flex;align-items:center;justify-content:space-between;margin:0 -72px;padding:0 72px}
.page.dark .footer{border-top-color:rgba(255,255,255,.14)}
.who{display:flex;align-items:center;gap:18px}
.avatar{width:58px;height:58px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--dark2));color:#fff;font-weight:900;font-size:24px;display:flex;align-items:center;justify-content:center}
.name{font-weight:800;font-size:24px}.role{font-size:18px;color:var(--muted);margin-top:2px}
.page.dark .role{color:rgba(255,255,255,.72)}
.tag{font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:18px;color:var(--muted)}
/* flow */
.flow{display:flex;flex-direction:column;gap:0}
.stage{display:flex;gap:24px;align-items:stretch;background:var(--card);border:2px solid var(--line);border-radius:22px;padding:22px 26px;box-shadow:0 6px 18px rgba(15,23,42,.05)}
.stage .num{min-width:58px;height:58px;border-radius:16px;background:var(--dark2);color:#fff;font-weight:900;font-size:26px;display:flex;align-items:center;justify-content:center}
.stage.hl{border-color:var(--accent);background:var(--soft)}
.stage.hl .num{background:var(--accent)}
.stage h3{font-size:29px;font-weight:800;line-height:1.2}
.stage p{font-size:22px;line-height:1.4;color:var(--muted);margin-top:6px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.chip{font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:16px;background:var(--chip);color:var(--dark2);padding:5px 12px;border-radius:999px;font-weight:700}
.arrow{height:30px;display:flex;justify-content:center;align-items:center;color:var(--accent);font-size:26px;font-weight:900}
/* compare */
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.col{border-radius:24px;padding:30px;background:var(--card);border:2px solid var(--line)}
.col.good{border-color:var(--accent);background:var(--soft)}
.col h3{font-size:32px;font-weight:900;margin-bottom:18px}
.col.bad h3{color:var(--muted)}.col.good h3{color:var(--accentText)}
.col li{list-style:none;font-size:24px;line-height:1.35;padding:12px 0;border-top:1px solid var(--line)}
.col li:first-of-type{border-top:none}
/* stat */
.big{font-size:230px;font-weight:900;letter-spacing:-8px;line-height:1;background:linear-gradient(135deg,var(--accent),var(--dark2));-webkit-background-clip:text;background-clip:text;color:transparent}
.statline{font-size:38px;font-weight:800;line-height:1.25;margin-top:18px}
.points{margin-top:40px;display:flex;flex-direction:column;gap:16px}
.pt{font-size:26px;line-height:1.4;padding-left:34px;position:relative}
.pt:before{content:'';position:absolute;left:0;top:12px;width:16px;height:16px;border-radius:4px;background:var(--accent)}
.takeaway{margin-top:30px;background:linear-gradient(135deg,var(--dark),var(--dark2));color:#fff;border-radius:22px;padding:26px 30px;font-size:25px;line-height:1.4;font-weight:600}
.takeaway b{color:var(--onDark)}
.source{font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:15px;color:var(--muted);margin-top:14px}
/* carousel */
.slide-body{font-size:34px;line-height:1.45;margin-top:30px;color:var(--ink);opacity:.86}
.page.dark .slide-body{color:#fff;opacity:.88}
.bul{margin-top:30px;display:flex;flex-direction:column;gap:20px}
.bul .pt{font-size:31px}
.page.dark .pt:before{background:var(--onDark)}
pre{margin-top:30px;background:var(--dark);color:var(--soft);font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:24px;line-height:1.5;padding:28px;border-radius:18px;white-space:pre-wrap;border:1px solid rgba(255,255,255,.08)}
.pager{font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:20px;color:var(--muted)}
.page.dark .pager{color:rgba(255,255,255,.6)}
.swipe{font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:22px;color:var(--accentText);font-weight:700}
.page.dark .swipe{color:var(--onDark)}
.cover h1{font-size:88px}
"""

# ---------------------------------------------------------------------------
# Palette library. Every visual picks one; consecutive visuals never repeat.
# Keys: bg (light page), card, ink, muted, line, accent (fills), accentText
# (accent used as text on light bg, AA contrast), soft (tint), dark, dark2
# (gradient for dark slides/takeaway), onDark (accent text on dark), chip.
# ---------------------------------------------------------------------------
PALETTES = {
  "ocean-teal":     dict(bg="#F4F8FB", card="#FFFFFF", ink="#0B1220", muted="#5B6B80", line="#DCE3EC", accent="#0EA5A4", accentText="#0B7A79", soft="#D5F3F1", dark="#0F2440", dark2="#1F3A5F", onDark="#5EEAD4", chip="#E6F0F5"),
  "midnight-violet":dict(bg="#F8F7FF", card="#FFFFFF", ink="#1A1537", muted="#625C80", line="#E3E0F5", accent="#7C3AED", accentText="#6D28D9", soft="#EDE9FE", dark="#1E1B4B", dark2="#3B1D7A", onDark="#C4B5FD", chip="#EFEBFF"),
  "sunset-coral":   dict(bg="#FFF8F4", card="#FFFFFF", ink="#2A1618", muted="#7A5A55", line="#F3DED6", accent="#F2545B", accentText="#C8323A", soft="#FFE1DC", dark="#2B1B2E", dark2="#5C2340", onDark="#FFB4A2", chip="#FFEDE7"),
  "emerald-forest": dict(bg="#F4FAF7", card="#FFFFFF", ink="#0B201B", muted="#4F6B63", line="#D5E8E0", accent="#10B981", accentText="#047857", soft="#D1FAE5", dark="#062A24", dark2="#0F4C3F", onDark="#6EE7B7", chip="#E3F4EC"),
  "royal-gold":     dict(bg="#F7F8FC", card="#FFFFFF", ink="#0B1633", muted="#56627D", line="#DDE2EF", accent="#2F5BEA", accentText="#1D4ED8", soft="#E0E8FF", dark="#0B1E4A", dark2="#1B2F6E", onDark="#FACC15", chip="#E8EDFB"),
  "plum-peach":     dict(bg="#FFF7FA", card="#FFFFFF", ink="#2A0E2E", muted="#76566F", line="#F1DCE7", accent="#DB2777", accentText="#BE185D", soft="#FCE7F3", dark="#3B0A45", dark2="#6B1E5E", onDark="#FDBA8C", chip="#FBEAF2"),
  "charcoal-amber": dict(bg="#FAF8F3", card="#FFFFFF", ink="#18181B", muted="#5F5E66", line="#E7E3D8", accent="#F59E0B", accentText="#B45309", soft="#FEF3C7", dark="#18181B", dark2="#2E2B25", onDark="#FBBF24", chip="#F4EFE2"),
  "deep-aqua":      dict(bg="#F2FAFC", card="#FFFFFF", ink="#062431", muted="#4E6A76", line="#D3E8EF", accent="#06B6D4", accentText="#0E7490", soft="#CFFAFE", dark="#082F49", dark2="#0C4A6E", onDark="#67E8F9", chip="#E1F3F8"),
  "crimson-slate":  dict(bg="#F9FAFB", card="#FFFFFF", ink="#111827", muted="#5B6474", line="#E1E4EA", accent="#E11D48", accentText="#BE123C", soft="#FFE4E6", dark="#1F2937", dark2="#374151", onDark="#FDA4AF", chip="#EEF0F4"),
  "aurora":         dict(bg="#F6F7FE", card="#FFFFFF", ink="#0F172A", muted="#566079", line="#DEE1F3", accent="#6366F1", accentText="#4F46E5", soft="#E0E7FF", dark="#0F172A", dark2="#312E81", onDark="#22D3EE", chip="#E9EBFB"),
  "lime-graphite":  dict(bg="#F7F9F2", card="#FFFFFF", ink="#141A12", muted="#5A6353", line="#E0E6D6", accent="#65A30D", accentText="#4D7C0F", soft="#ECFCCB", dark="#1A1F16", dark2="#2F3A22", onDark="#BEF264", chip="#EEF3E3"),
  "terracotta-sand":dict(bg="#FBF6F1", card="#FFFFFF", ink="#2B1A12", muted="#76604F", line="#EDE0D3", accent="#C2410C", accentText="#9A3412", soft="#FFEDD5", dark="#3A2218", dark2="#5E3322", onDark="#FDBA74", chip="#F6EADF"),
}
PALETTE_ORDER = list(PALETTES)

def pick_palette(spec):
    """Explicit spec["palette"] wins (name or 'random'). Otherwise rotate by
    PKT day number so consecutive runs always differ and all get used."""
    import datetime, random
    name = spec.get("palette")
    if name in PALETTES:
        return name
    if name == "random":
        return random.choice(PALETTE_ORDER)
    pkt = (datetime.datetime.utcnow() + datetime.timedelta(hours=5)).date()
    # Two visual slots per week (Wed = slot 0, Fri+ = slot 1): every visual
    # gets the next palette in order, so all 12 are used before any repeats.
    week = (pkt - datetime.date(2026, 1, 5)).days // 7
    slot = 1 if pkt.weekday() >= 4 else 0
    return PALETTE_ORDER[(week * 2 + slot) % len(PALETTE_ORDER)]

def palette_vars(p):
    return ":root{" + ";".join(f"--{k}:{v}" for k, v in PALETTES[p].items()) + "}"


def e(s):
    """escape but allow *word* -> teal emphasis"""
    s = html.escape(str(s or ""))
    parts = s.split("*")
    return "".join(f"<em>{p}</em>" if i % 2 else p for i, p in enumerate(parts))

def footer(right):
    return f"""<div class="footer"><div class="who"><div class="avatar">SJ</div>
<div><div class="name">{HANDLE}</div><div class="role">{ROLE}</div></div></div>{right}</div>"""

def infographic(s):
    lay = s.get("layout", "flow")
    head = f"""<div class="kicker">{e(s.get('kicker','Architecture'))}</div><h1>{e(s['title'])}</h1>
{f'<div class="sub">{e(s["subtitle"])}</div>' if s.get('subtitle') else ''}"""
    if lay == "flow":
        items = []
        stages = s["stages"]
        for i, st in enumerate(stages):
            chips = "".join(f'<span class="chip">{e(c)}</span>' for c in st.get("chips", []))
            items.append(f"""<div class="stage {'hl' if st.get('highlight') else ''}"><div class="num">{i+1}</div>
<div><h3>{e(st['name'])}</h3><p>{e(st.get('desc',''))}</p>{f'<div class="chips">{chips}</div>' if chips else ''}</div></div>""")
            if i < len(stages) - 1:
                items.append('<div class="arrow">↓</div>')
        body = f'<div class="flow">{"".join(items)}</div>'
    elif lay == "compare":
        L, R = s["left"], s["right"]
        body = f"""<div class="cmp"><div class="col bad"><h3>{e(L['title'])}</h3><ul>{''.join(f'<li>{e(x)}</li>' for x in L['items'])}</ul></div>
<div class="col good"><h3>{e(R['title'])}</h3><ul>{''.join(f'<li>{e(x)}</li>' for x in R['items'])}</ul></div></div>"""
    else:  # stat
        body = f"""<div class="big">{e(s['stat'])}</div><div class="statline">{e(s['statline'])}</div>
<div class="points">{''.join(f'<div class="pt">{e(p)}</div>' for p in s.get('points', []))}</div>"""
    tk = f'<div class="takeaway">{e(s["takeaway"]).replace("<em>","<b>").replace("</em>","</b>")}</div>' if s.get("takeaway") else ""
    src = f'<div class="source">Source: {e(s["source"])}</div>' if s.get("source") else ""
    return f"""<div class="page">{head}<div class="content">{body}{tk}{src}</div>{footer('<div class="tag">save ↗ share ↻</div>')}</div>"""

def slide(sl, i, n):
    dark = sl.get("dark", i == 0 or i == n - 1)
    cls = "page" + (" dark" if dark else "") + (" cover" if i == 0 else "")
    parts = [f'<div class="kicker">{e(sl.get("kicker",""))}</div>' if sl.get("kicker") else "",
             f'<h1>{e(sl.get("title",""))}</h1>']
    if sl.get("body"): parts.append(f'<div class="slide-body">{e(sl["body"])}</div>')
    if sl.get("bullets"): parts.append('<div class="bul">' + "".join(f'<div class="pt">{e(b)}</div>' for b in sl["bullets"]) + "</div>")
    if sl.get("code"): parts.append(f'<pre>{html.escape(sl["code"])}</pre>')
    right = '<div class="swipe">swipe →</div>' if i < n - 1 else '<div class="swipe">follow for more ↗</div>'
    return f"""<div class="{cls}"><div class="pager">{i+1:02d} / {n:02d}</div><div class="content">{''.join(parts)}</div>{footer(right)}</div>"""

def shot(pw_page, inner, path, pal):
    pw_page.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{palette_vars(pal)}{CSS}</style></head><body>{inner}</body></html>", wait_until="networkidle")
    pw_page.wait_for_timeout(400)
    pw_page.screenshot(path=path, clip={"x": 0, "y": 0, "width": W, "height": H})

def main():
    spec = json.load(open(sys.argv[1]))
    pal = pick_palette(spec)
    print("PALETTE:", pal)
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    with sync_playwright() as p:
        exe = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") and os.path.isfile("/opt/pw-browsers/chromium") else None
        b = p.chromium.launch(args=["--no-sandbox"], **({"executable_path": exe} if exe else {}))
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        if spec["type"] == "infographic":
            shot(pg, infographic(spec), os.path.join(out, "infographic.png"), pal)
            print(os.path.join(out, "infographic.png"))
        else:
            slides = spec["slides"]; pngs = []
            for i, sl in enumerate(slides):
                f = os.path.join(out, f"slide-{i+1:02d}.png"); shot(pg, slide(sl, i, len(slides)), f, pal); pngs.append(f)
            import base64
            pdf = os.path.join(out, spec.get("filename", "carousel") + ".pdf")
            imgs = "".join(f'<img src="data:image/png;base64,{base64.b64encode(open(f,"rb").read()).decode()}" style="display:block;width:1080px;height:1350px;page-break-after:always">' for f in pngs)
            pg.set_content(f"<html><head><style>@page{{size:1080px 1350px;margin:0}}body{{margin:0}}</style></head><body>{imgs}</body></html>")
            pg.pdf(path=pdf, width="1080px", height="1350px", print_background=True, margin={"top":"0","bottom":"0","left":"0","right":"0"})
            print("\n".join(pngs + [pdf]))
        b.close()

if __name__ == "__main__":
    main()
