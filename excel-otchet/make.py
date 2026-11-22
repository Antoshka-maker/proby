"""Образец: из сырой выгрузки чеков (демо-данные) собирается отчёт с формулами и диаграммами"""
import random, datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.utils import get_column_letter as L
random.seed(7)
POINTS={"Ленина, 12":1.25,"Вокзал":1.05,"ТЦ «Галерея»":0.9,"Университет":0.75}
GOODS={"Капучино":(220,.26),"Латте":(240,.2),"Американо":(170,.14),"Раф":(290,.1),"Флэт уайт":(260,.07),"Круассан":(150,.12),"Сырник":(180,.06),"Чай":(140,.05)}
names=list(GOODS);w=[GOODS[g][1] for g in names]
rows=[];d0=dt.date(2026,8,1)
for day in range(92):
    d=d0+dt.timedelta(day);wk=1.25 if d.weekday()>=5 else 1
    for p,k in POINTS.items():
        if p=="Университет" and d.weekday()>=5: k*=.45
        for _ in range(int(random.gauss(70,8)*k*wk*(1+day/400))):
            g=random.choices(names,w)[0];q=1 if random.random()<.85 else 2
            rows.append([d,p,g,q,GOODS[g][0],None])
wb=Workbook();raw=wb.active;raw.title="Выгрузка"
raw.append(["Дата","Точка","Товар","Кол-во","Цена","Сумма"])
for i,r in enumerate(rows,2):
    r[5]=f"=D{i}*E{i}";raw.append(r);raw[f"A{i}"].number_format="DD.MM.YYYY"
N=len(rows)+1
H=PatternFill("solid",fgColor="3B2416");WF=Font(bold=True,color="FFFFFF");thin=Side(style="thin",color="E6DED6")
def head(ws,row=1):
    for c in ws[row]:
        if c.value is not None:c.fill=H;c.font=WF;c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
head(raw);raw.freeze_panes="A2";raw.auto_filter.ref=f"A1:F{N}"
for i,wd in enumerate([12,16,14,8,8,10],1):raw.column_dimensions[L(i)].width=wd
rng=lambda col:f"Выгрузка!${col}$2:${col}${N}"
ws=wb.create_sheet("Отчёт",0)
ws["A1"]="Сеть кофеен: продажи за август–октябрь 2026";ws["A1"].font=Font(bold=True,size=18,color="3B2416")
ws["A2"]="Демо-данные. Все цифры считаются формулами из листа «Выгрузка»: замените выгрузку, отчёт пересчитается";ws["A2"].font=Font(italic=True,color="8A7A6E")
kp=[("Выручка, ₽",f"=SUM({rng('F')})","#,##0"),("Чеков",f"=COUNTA({rng('A')})","#,##0"),("Средний чек, ₽","=B4/B5","#,##0"),("Лучшая точка",f'=INDEX(A10:A13,MATCH(MAX(E10:E13),E10:E13,0))',"@")]
for i,(n,f,fmt) in enumerate(kp,4):
    ws[f"A{i}"]=n;ws[f"B{i}"]=f;ws[f"B{i}"].number_format=fmt;ws[f"A{i}"].font=Font(color="6B5A4E");ws[f"B{i}"].font=Font(bold=True,size=14)
months=[(8,"Август"),(9,"Сентябрь"),(10,"Октябрь")]
ws.append([]);ws["A9"]="Точка";
for j,(m,n) in enumerate(months):ws.cell(9,2+j,n)
ws.cell(9,5,"Итого");ws.cell(9,6,"Рост окт/авг")
for i,p in enumerate(POINTS,10):
    ws.cell(i,1,p)
    for j,(m,n) in enumerate(months):
        a=dt.date(2026,m,1);b=dt.date(2026,m+1,1)
        c=ws.cell(i,2+j,f'=SUMIFS({rng("F")},{rng("B")},$A{i},{rng("A")},">="&DATE({a.year},{a.month},1),{rng("A")},"<"&DATE({b.year},{b.month},1))');c.number_format="#,##0"
    ws.cell(i,5,f"=SUM(B{i}:D{i})").number_format="#,##0";ws.cell(i,6,f"=D{i}/B{i}-1").number_format="+0%;-0%"
ws.cell(14,1,"Всего").font=Font(bold=True)
for j in range(2,6):ws.cell(14,j,f"=SUM({L(j)}10:{L(j)}13)").number_format="#,##0";ws.cell(14,j).font=Font(bold=True)
head(ws,9)
ws.conditional_formatting.add("B10:D13",ColorScaleRule(start_type="min",start_color="FFF3E6",end_type="max",end_color="E0905A"))
ws.conditional_formatting.add("F10:F13",DataBarRule(start_type="num",start_value=0,end_type="max",color="7BB661"))
ws["A17"]="Товар";ws["B17"]="Продано, шт";ws["C17"]="Выручка, ₽";ws["D17"]="Доля"
for i,g in enumerate(names,18):
    ws.cell(i,1,g);ws.cell(i,2,f'=SUMIFS({rng("D")},{rng("C")},A{i})').number_format="#,##0"
    ws.cell(i,3,f'=SUMIFS({rng("F")},{rng("C")},A{i})').number_format="#,##0";ws.cell(i,4,f"=C{i}/$B$4").number_format="0%"
head(ws,17);ws.conditional_formatting.add("C18:C25",DataBarRule(start_type="min",end_type="max",color="C8823F"))
for i,wd in enumerate([24,14,14,14,14,14],1):ws.column_dimensions[L(i)].width=wd
ch=BarChart();ch.title="Выручка по точкам и месяцам";ch.y_axis.title="₽";ch.height=8.5;ch.width=16
ch.add_data(Reference(ws,min_col=2,max_col=4,min_row=9,max_row=13),titles_from_data=True);ch.set_categories(Reference(ws,min_col=1,min_row=10,max_row=13));ws.add_chart(ch,"H3")
c2=BarChart();c2.type="bar";c2.title="Выручка по товарам";c2.legend=None;c2.height=8.5;c2.width=16
c2.add_data(Reference(ws,min_col=3,min_row=17,max_row=25),titles_from_data=True);c2.set_categories(Reference(ws,min_col=1,min_row=18,max_row=25));ws.add_chart(c2,"H21")
# по дням
dd=wb.create_sheet("По дням");dd.append(["Дата","Выручка, ₽"])
for k in range(92):
    i=k+2;dd.cell(i,1,d0+dt.timedelta(k)).number_format="DD.MM";dd.cell(i,2,f'=SUMIFS({rng("F")},{rng("A")},A{i})').number_format="#,##0"
head(dd);lc=LineChart();lc.title="Выручка по дням";lc.height=9;lc.width=24;lc.legend=None
lc.add_data(Reference(dd,min_col=2,min_row=1,max_row=93),titles_from_data=True);lc.set_categories(Reference(dd,min_col=1,min_row=2,max_row=93));dd.add_chart(lc,"D2")
wb.save("otchet-kofeyni.xlsx");print(len(rows),"чеков")
