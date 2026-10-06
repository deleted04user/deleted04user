"""Self-contained animated profile art. Daily refresh uses Python stdlib only."""
from __future__ import annotations
import argparse
import json
import re
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = "deleted04user"
BG, BORDER = "#0b111b", "#243247"
TEXT, MUTED, CYAN, GREEN = "#e4edf8", "#a4b5ca", "#69d9ed", "#7ce5aa"
FONT = "'Cascadia Code','SFMono-Regular',Consolas,'Liberation Mono',monospace"

class ContributionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.tips = {}, {}
        self.tip_id, self.tip_text = None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("data-date") and a.get("data-level") is not None:
            key = a.get("id")
            if not key or key in self.cells:
                raise ValueError("Missing or duplicate calendar cell id")
            self.cells[key] = {"date": a["data-date"], "level": int(a["data-level"]),
                "count": int(a["data-count"]) if "data-count" in a else None}
        if tag == "tool-tip":
            self.tip_id, self.tip_text = a.get("for"), []

    def handle_data(self, data):
        if self.tip_id:
            self.tip_text.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tip_id:
            self.tips[self.tip_id] = " ".join("".join(self.tip_text).split())
            self.tip_id = None

    def days(self):
        result = []
        for key, original in self.cells.items():
            cell = dict(original)
            if cell["count"] is None:
                match = re.match(r"(No|[\d,]+) contributions?\b", self.tips.get(key, ""))
                if not match:
                    raise ValueError(f"Cannot read contribution count for {cell['date']}")
                cell["count"] = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            if not 0 <= cell["level"] <= 4 or cell["count"] < 0:
                raise ValueError("Invalid contribution level or count")
            date.fromisoformat(cell["date"])
            result.append(cell)
        result.sort(key=lambda d: d["date"])
        if not 300 <= len(result) <= 380:
            raise ValueError(f"Expected a full calendar, received {len(result)} days")
        for a, b in zip(result, result[1:]):
            if date.fromisoformat(b["date"]) - date.fromisoformat(a["date"]) != timedelta(days=1):
                raise ValueError("Calendar dates are duplicated or incomplete")
        return result

def summarize(days):
    longest = running = 0
    for day in days:
        running = running + 1 if day["count"] else 0
        longest = max(longest, running)
    tail = days[:-1] if days and not days[-1]["count"] else days
    current = 0
    for day in reversed(tail):
        if not day["count"]:
            break
        current += 1
    return {"total": sum(d["count"] for d in days), "active_days": sum(d["count"] > 0 for d in days),
            "longest_streak": longest, "current_streak": current}

def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8", newline="\n")
    temp.replace(path)

def fetch():
    url = f"https://github.com/users/{USER}/contributions"
    request = Request(url, headers={"User-Agent": "OussamaProfileArt/1.0", "Accept-Language": "en-US"})
    with urlopen(request, timeout=45) as response:
        markup = response.read().decode("utf-8")
    parser = ContributionParser()
    parser.feed(markup)
    days = parser.days()
    today = datetime.now(timezone.utc).date()
    last = date.fromisoformat(days[-1]["date"])
    if not today - timedelta(days=2) <= last <= today + timedelta(days=1):
        raise ValueError("GitHub returned a stale calendar")
    payload = {"username": USER, "source": url, "fetched_on": today.isoformat(),
               "period_start": days[0]["date"], "period_end": days[-1]["date"],
               "stats": summarize(days), "days": days}
    atomic_write(ROOT / "data/contributions.json", json.dumps(payload, indent=2) + "\n")
    return payload

def text(x, y, value, size=14, fill=TEXT, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" {extra}>{escape(str(value))}</text>'

def svg(width, height, title, description, content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<style>text{{font-family:{FONT}}}.reveal{{animation:reveal .5s both}}@keyframes reveal{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1;transform:translateY(0)}}}}@media(prefers-reduced-motion:reduce){{.reveal{{animation:none}}}}</style>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="16" fill="{BG}" stroke="{BORDER}"/>
{content}
</svg>\n'''

def chrome(label, width):
    return (f'<path d="M1 44H{width-1}" stroke="{BORDER}"/>'
            '<circle cx="22" cy="23" r="4" fill="#ff7b72"/><circle cx="37" cy="23" r="4" fill="#e8c56a"/><circle cx="52" cy="23" r="4" fill="#7ce5aa"/>'
            + text(72, 27, label, 11, MUTED))

def header():
    content = chrome("oussama@github: ~", 960)
    content += text(30, 79, "$ whoami", 12, GREEN)
    content += text(30, 120, "OUSSAMA OULKAID", 30, TEXT, 'font-weight="700" letter-spacing="1"')
    content += text(30, 153, "Software & AI Engineering  /  EMSI Casablanca  /  Morocco", 14, MUTED)
    content += '<rect x="749" y="82" width="180" height="36" rx="18" fill="#142b26" stroke="#295e47"/>'
    content += '<circle cx="765" cy="100" r="4" fill="#7ce5aa"/>' + text(777, 105, "OPEN TO INTERNSHIPS", 11, GREEN)
    atomic_write(ROOT / "assets/header.svg", svg(960, 184, "Oussama Oulkaid", "Software and AI engineering student at EMSI Casablanca, Morocco. Open to internships.", content))

def info():
    content = chrome("~/profile  $ neofetch", 560)
    content += text(28, 83, "deleted04user", 23, CYAN, 'font-weight="700"')
    content += text(28, 109, "----------------------------", 14, MUTED)
    rows = [("Role", "Software & AI engineering student"), ("School", "EMSI Casablanca"),
            ("Focus", "LLMs / RAG / Machine Learning"), ("Build", "Models -> APIs -> interfaces"),
            ("AI", "Python / Qwen / FAISS / XGBoost"), ("Web", "FastAPI / React / SQL"),
            ("Tools", "Git / Docker / Linux"), ("Seek", "AI, data & software internships")]
    for i, (key, value) in enumerate(rows):
        y = 147 + i * 29
        content += f'<g class="reveal" style="animation-delay:{.2+i*.1:.2f}s">' + text(28, y, key, 13, CYAN) + text(113, y, value, 13) + '</g>'
    content += f'<path d="M28 378H532" stroke="{BORDER}"/>'
    content += text(28, 404, "Source-grounded AI. Reproducible experiments.", 12, GREEN)
    content += text(28, 426, "Useful interfaces. Thoughtful engineering.", 12, MUTED)
    atomic_write(ROOT / "assets/info-card.svg", svg(560, 448, "Oussama's engineering profile", "Software and AI student focused on LLMs, RAG, machine learning, FastAPI and React. Open to internships.", content))

def portrait(source):
    from PIL import Image, ImageDraw, ImageOps, ImageEnhance
    image = Image.open(source).convert("RGB").resize((460, 460))
    # Subject outline follows the current public avatar; omit the wall from the character grid.
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).polygon([(0,450),(20,350),(47,303),(135,273),(171,250),
        (164,199),(150,181),(154,162),(146,122),(159,72),(184,46),(232,29),
        (283,39),(307,66),(318,113),(305,163),(306,186),(292,214),(286,253),
        (323,277),(374,292),(405,344),(430,460)], fill=255)
    gray = ImageEnhance.Contrast(ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)).enhance(1.15)
    canvas = Image.new("L", image.size, 255)
    canvas.paste(gray, mask=mask)
    grid = canvas.resize((76, 43), Image.Resampling.LANCZOS)
    ramp = " .:-=+*#%@"
    rows = ["".join(ramp[min(len(ramp)-1, int((255-grid.getpixel((x,y)))/256*len(ramp)))] for x in range(76)) for y in range(43)]
    content = chrome("~/identity  $ cat portrait.ascii", 380)
    content += '<defs>'
    for i in range(len(rows)):
        content += f'<clipPath id="row{i}"><rect x="20" y="{58+i*7.9}" width="340" height="9"><animate attributeName="width" from="0" to="340" begin="{.12+i*.025:.3f}s" dur=".18s" fill="freeze"/></rect></clipPath>'
    content += '</defs>'
    for i, row in enumerate(rows):
        content += text(20, round(65+i*7.9, 2), row, 7.2, "#c6d6e6", f'xml:space="preserve" clip-path="url(#row{i})" textLength="340" lengthAdjust="spacingAndGlyphs"')
    content += f'<path d="M20 410H360" stroke="{BORDER}"/>' + text(20, 433, "[ identity loaded ]", 11, GREEN)
    atomic_write(ROOT / "assets/oussama-ascii.svg", svg(380, 448, "ASCII portrait of Oussama Oulkaid", "Monochrome ASCII portrait generated from Oussama's public GitHub avatar; reveals once line by line.", content))

def heatmap(payload):
    days, stats = payload["days"], payload["stats"]
    start = date.fromisoformat(days[0]["date"])
    origin = start - timedelta(days=(start.weekday()+1) % 7)
    columns = ((date.fromisoformat(days[-1]["date"])-origin).days // 7) + 1
    step = min(16, 850 / columns)
    palette = ["#172536", "#164d43", "#217b63", "#3fb58a", "#7ce5aa"]
    content = chrome("~/activity  $ contributions --last-year", 960)
    content += text(28, 80, f"{stats['total']:,} contributions", 23, TEXT, 'font-weight="700"')
    content += text(28, 104, "One commit at a time. One useful system at a time.", 12, MUTED)
    content += text(728, 80, f"updated {payload['fetched_on']}", 11, MUTED)
    month = None
    for day in days:
        d = date.fromisoformat(day["date"])
        col, row = (d-origin).days // 7, (d.weekday()+1) % 7
        x, y = 62 + col*step, 143 + row*16
        if (d.year, d.month) != month:
            content += text(round(x,2), 132, d.strftime("%b"), 10, MUTED)
            month = (d.year, d.month)
        content += f'<rect class="reveal" x="{x:.2f}" y="{y}" width="{step-3:.2f}" height="13" rx="3" fill="{palette[day["level"]]}" style="animation-delay:{col*.014+row*.022:.3f}s"><title>{day["date"]}: {day["count"]} contributions</title></rect>'
    for row, label in [(1,"Mon"),(3,"Wed"),(5,"Fri")]:
        content += text(28, 153+row*16, label, 10, MUTED)
    content += text(28, 283, f"{stats['active_days']} active days  /  {stats['longest_streak']}-day longest streak", 12, MUTED)
    content += text(755, 283, "Less", 10, MUTED)
    for i, color in enumerate(palette):
        content += f'<rect x="{790+i*17}" y="273" width="13" height="13" rx="3" fill="{color}"/>'
    content += text(885, 283, "More", 10, MUTED)
    description = f"GitHub contribution calendar from {payload['period_start']} to {payload['period_end']}. {stats['total']} contributions, {stats['active_days']} active days, longest streak {stats['longest_streak']} days."
    atomic_write(ROOT / "assets/contrib-heatmap.svg", svg(960, 306, "Oussama's GitHub contributions", description, content))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--portrait", type=Path)
    args = parser.parse_args()
    if args.identity:
        header()
        info()
    if args.portrait:
        portrait(args.portrait)
    if args.refresh:
        payload = fetch()
        heatmap(payload)
        print(f"Rendered {len(payload['days'])} days / {payload['stats']['total']} contributions")
    if not any([args.refresh, args.identity, args.portrait]):
        parser.error("Choose --refresh, --identity or --portrait")

if __name__ == "__main__":
    main()
