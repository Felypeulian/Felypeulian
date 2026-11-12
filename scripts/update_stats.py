"""Gera cartões SVG a partir dos repositórios públicos, sem serviços de imagens."""

import json
import os
import sys
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree

OWNER = "Felypeulian"
ROOT = Path(__file__).resolve().parents[1]
COLORS = {"PHP": "#a5a9ec", "HTML": "#f5826a", "CSS": "#79b8ff", "Python": "#f2cc60", "JavaScript": "#f1e05a"}


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Felypeulian-profile"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
        return json.load(response)


def collect():
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        repos.extend(repo for repo in batch if not repo["private"] and not repo["fork"])
        if len(batch) < 100:
            break
        page += 1
    languages = Counter()
    for repo in repos:
        # O script de manutenção do perfil não representa as linguagens dos projetos.
        if repo["name"].lower() != OWNER.lower():
            languages.update(api(f"/repos/{OWNER}/{repo['name']}/languages"))
    return repos, languages


def text(x, y, value, size=13, color="#c9d1d9", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'


def card(title, body, description):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="230" viewBox="0 0 420 230" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>'
        '<rect x="1" y="1" width="418" height="228" rx="14" fill="#0d1117" stroke="#30363d"/>'
        '<g font-family="Segoe UI,Arial,sans-serif">'
        + text(24, 36, title, 18, "#f0f6fc", 'font-weight="600"')
        + '<path d="M24 51H396" stroke="#21262d"/>'
        + body
        + text(24, 213, "Atualizado em " + date.today().strftime("%d/%m/%Y"), 11, "#8b949e")
        + '</g></svg>\n'
    )


def render(repos, languages):
    rows = [("Repositórios públicos próprios", len(repos)),
            ("Estrelas recebidas", sum(repo["stargazers_count"] for repo in repos)),
            ("Linguagens nos projetos", len(languages))]
    stats = "".join(text(24, 85 + i * 39, label) + text(392, 85 + i * 39, value, 24, "#79b8ff", 'text-anchor="end" font-weight="600"') for i, (label, value) in enumerate(rows))
    total = sum(languages.values())
    bars = ""
    for i, (name, amount) in enumerate(languages.most_common(4)):
        y = 76 + i * 29
        percent = amount / total * 100
        label = f"{percent:.1f}%" if percent >= 0.1 else "<0.1%"
        bars += text(24, y, name) + text(396, y, label, 12, "#8b949e", 'text-anchor="end"')
        bars += f'<rect x="24" y="{y + 6}" width="372" height="5" rx="2" fill="#21262d"/>'
        bars += f'<rect x="24" y="{y + 6}" width="{372 * amount / total:.2f}" height="5" rx="2" fill="{COLORS.get(name, "#7ee787")}"/>'
    if not total:
        bars = text(24, 95, "Nenhuma linguagem detectada ainda.")
    bars += text(24, 195, "Proporção de código público em bytes · sem forks", 10, "#8b949e")
    return {
        "github-stats.svg": card("Atividade no GitHub", stats, "; ".join(f"{label}: {value}" for label, value in rows)),
        "top-languages.svg": card("Linguagens nos projetos", bars, "Distribuição do código público, excluindo forks e o repositório do perfil."),
    }


if __name__ == "__main__":
    if "--test" in sys.argv:
        for data in (Counter(), Counter({"PHP": 300, "HTML": 100, "A&B": 5})):
            cards = render([{"stargazers_count": 2}], data)
            for svg in cards.values():
                ElementTree.fromstring(svg)
                assert "nan" not in svg.lower() and 'width="-' not in svg
            if data:
                assert "A&amp;B" in cards["top-languages.svg"]
        print("OK: cartões válidos, dados vazios e nomes escapados.")
    else:
        repos, languages = collect()
        cards = render(repos, languages)
        (ROOT / "assets").mkdir(exist_ok=True)
        for name, svg in cards.items():
            ElementTree.fromstring(svg)
            (ROOT / "assets" / name).write_text(svg, encoding="utf-8")
        print(f"OK: {len(repos)} repositórios públicos; linguagens: {dict(languages)}")
