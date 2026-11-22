"""Парсер каталога books.toscrape.com (учебный сайт для тренировки парсинга).
Собирает все книги по категориям: название, категория, цена, рейтинг, наличие, ссылка.
Результат: Excel с каталогом и сводкой по категориям с диаграммой.
Запуск: python parser.py  (нужны requests, beautifulsoup4, openpyxl)"""
import time, re, logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.utils import get_column_letter

BASE = "https://books.toscrape.com/"
RATING = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
s = requests.Session(); s.headers["User-Agent"] = "catalog-parser/1.0"

def get(url, tries=3):
    for i in range(tries):
        try:
            r = s.get(url, timeout=20); r.raise_for_status(); r.encoding = "utf-8"
            return BeautifulSoup(r.text, "html.parser")
        except requests.RequestException as e:
            logging.warning("повтор %s: %s", url, e); time.sleep(2 * (i + 1))
    raise RuntimeError(url)

def categories():
    soup = get(BASE)
    for a in soup.select(".side_categories ul li ul li a"):
        yield a.get_text(strip=True), urljoin(BASE, a["href"])

def books(cat, url):
    while url:
        soup = get(url)
        for b in soup.select("article.product_pod"):
            a = b.select_one("h3 a")
            yield {"Название": a["title"], "Категория": cat,
                   "Цена, £": float(re.sub(r"[^\d.]", "", b.select_one(".price_color").text)),
                   "Рейтинг": RATING[b.select_one(".star-rating")["class"][1]],
                   "В наличии": "да" if "In stock" in b.select_one(".availability").text else "нет",
                   "Ссылка": urljoin(url, a["href"])}
        nxt = soup.select_one("li.next a")
        url = urljoin(url, nxt["href"]) if nxt else None
        time.sleep(0.3)  # не нагружаем сайт

def save(rows, path):
    wb = Workbook(); ws = wb.active; ws.title = "Каталог"
    head = list(rows[0]); ws.append(head)
    for r in rows: ws.append([r[h] for h in head])
    n = len(rows) + 1
    hf = PatternFill("solid", fgColor="1F2A44"); thin = Side(style="thin", color="D9DEE7")
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = hf; c.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 26
    for row in ws.iter_rows(min_row=2, max_row=n):
        for c in row: c.border = Border(bottom=thin)
        row[2].number_format = "0.00"; row[5].hyperlink = row[5].value; row[5].font = Font(color="2F6FDE", underline="single")
    for i, w in enumerate([52, 22, 10, 10, 11, 60], 1): ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"; ws.auto_filter.ref = f"A1:F{n}"
    ws.conditional_formatting.add(f"D2:D{n}", ColorScaleRule(start_type="num", start_value=1, start_color="F8696B", mid_type="num", mid_value=3, mid_color="FFEB84", end_type="num", end_value=5, end_color="63BE7B"))
    ws.conditional_formatting.add(f"C2:C{n}", DataBarRule(start_type="min", end_type="max", color="5B8DEF"))
    sv = wb.create_sheet("Сводка"); sv.append(["Категория", "Книг", "Средняя цена, £", "Средний рейтинг", "Доля с рейтингом 5"])
    cats = sorted({r["Категория"] for r in rows}, key=lambda c: -sum(r["Категория"] == c for r in rows))
    for i, c in enumerate(cats, 2):
        sv.append([c, f'=COUNTIF(Каталог!$B$2:$B${n},A{i})', f'=AVERAGEIF(Каталог!$B$2:$B${n},A{i},Каталог!$C$2:$C${n})',
                   f'=AVERAGEIF(Каталог!$B$2:$B${n},A{i},Каталог!$D$2:$D${n})', f'=COUNTIFS(Каталог!$B$2:$B${n},A{i},Каталог!$D$2:$D${n},5)/B{i}'])
        sv[f"C{i}"].number_format = "0.00"; sv[f"D{i}"].number_format = "0.0"; sv[f"E{i}"].number_format = "0%"
    for c in sv[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = hf
    for i, w in enumerate([26, 8, 16, 16, 20], 1): sv.column_dimensions[get_column_letter(i)].width = w
    sv.freeze_panes = "A2"
    ch = BarChart(); ch.type = "bar"; ch.title = "Книг в категории (15 крупнейших)"; ch.style = 10; ch.height = 12; ch.width = 18
    ch.add_data(Reference(sv, min_col=2, min_row=1, max_row=16), titles_from_data=True)
    ch.set_categories(Reference(sv, min_col=1, min_row=2, max_row=16)); ch.legend = None; ch.y_axis.majorGridlines = None
    sv.add_chart(ch, "G2"); wb.save(path)

if __name__ == "__main__":
    t = time.time(); rows = []
    for cat, url in categories():
        got = list(books(cat, url)); rows += got
        logging.info("%-22s %4d книг, всего %d", cat, len(got), len(rows))
    save(rows, "katalog-knig.xlsx")
    logging.info("готово: %d книг за %.0f с, файл katalog-knig.xlsx", len(rows), time.time() - t)
