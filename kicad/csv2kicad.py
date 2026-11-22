#!/usr/bin/env python3
"""CSV -> плата KiCad: линии и дуги становятся дорожками заданной ширины, окружности отверстиями.
Запуск: python3 csv2kicad.py primer.csv out.kicad_pcb --width 0.5 [--gerber outdir]
Проверено в KiCad 7.0.11 (pcbnew Python API)."""
import csv, math, argparse, os, pcbnew
mm = pcbnew.FromMM
def P(x, y): return pcbnew.VECTOR2I(mm(float(x)), mm(float(y)))

def arc_mid(x1, y1, x2, y2, cx, cy, direction):
    """Средняя точка дуги. direction: cw / ccw, как видно на экране KiCad (ось Y вниз)."""
    a1 = math.atan2(y1 - cy, x1 - cx); a2 = math.atan2(y2 - cy, x2 - cx)
    r = math.hypot(x1 - cx, y1 - cy)
    r2 = math.hypot(x2 - cx, y2 - cy)
    if abs(r - r2) > 0.01: raise ValueError(f'дуга: радиусы начала и конца расходятся ({r:.3f} и {r2:.3f})')
    d = a2 - a1
    if direction == 'cw':            # при оси Y вниз "по часовой" это рост угла
        while d <= 0: d += 2 * math.pi
    else:
        while d >= 0: d -= 2 * math.pi
    am = a1 + d / 2
    return cx + r * math.cos(am), cy + r * math.sin(am)

def build(csv_path, out_path, width, layer=pcbnew.F_Cu, plated=False):
    b = pcbnew.BOARD(); n = dict(line=0, arc=0, circle=0)
    xs, ys = [], []
    for i, row in enumerate(csv.DictReader(open(csv_path, encoding='utf-8-sig'), delimiter=';'), 2):
        t = row['type'].strip().lower(); f = lambda k: float(row[k].replace(',', '.'))
        try:
            if t == 'line':
                tr = pcbnew.PCB_TRACK(b); tr.SetStart(P(f('x1'), f('y1'))); tr.SetEnd(P(f('x2'), f('y2')))
                tr.SetWidth(mm(width)); tr.SetLayer(layer); b.Add(tr)
                xs += [f('x1'), f('x2')]; ys += [f('y1'), f('y2')]
            elif t == 'arc':
                mx, my = arc_mid(f('x1'), f('y1'), f('x2'), f('y2'), f('cx'), f('cy'), row['dir'].strip().lower())
                a = pcbnew.PCB_ARC(b); a.SetStart(P(f('x1'), f('y1'))); a.SetMid(P(mx, my)); a.SetEnd(P(f('x2'), f('y2')))
                a.SetWidth(mm(width)); a.SetLayer(layer); b.Add(a)
                xs += [f('x1'), f('x2'), mx]; ys += [f('y1'), f('y2'), my]
            elif t == 'circle':
                d = 2 * f('r'); fp = pcbnew.FOOTPRINT(b); fp.SetPosition(P(f('cx'), f('cy'))); fp.SetReference(f'H{n["circle"]+1}')
                fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
                pad = pcbnew.PAD(fp); pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE); pad.SetPosition(P(f('cx'), f('cy')))
                pad.SetDrillSize(pcbnew.VECTOR2I(mm(d), mm(d)))
                if plated:
                    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH); pad.SetSize(pcbnew.VECTOR2I(mm(d + 0.8), mm(d + 0.8))); pad.SetLayerSet(pad.PTHMask())
                else:
                    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); pad.SetSize(pcbnew.VECTOR2I(mm(d), mm(d))); pad.SetLayerSet(pad.UnplatedHoleMask())
                fp.Add(pad); b.Add(fp); xs += [f('cx')]; ys += [f('cy')]
            else: raise ValueError(f'неизвестный тип "{t}"')
            n[t] += 1
        except Exception as e:
            raise SystemExit(f'Строка {i}: {e}')
    # контур платы с полем 3 мм
    x0, x1, y0, y1 = min(xs) - 3, max(xs) + 3, min(ys) - 3, max(ys) + 3
    for a, c in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(P(*a)); s.SetEnd(P(*c)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); b.Add(s)
    pcbnew.SaveBoard(out_path, b); return b, n

def gerbers(b, outdir):
    os.makedirs(outdir, exist_ok=True)
    pc = pcbnew.PLOT_CONTROLLER(b); po = pc.GetPlotOptions(); po.SetOutputDirectory(outdir); po.SetUseGerberProtelExtensions(False)
    for name, lay in (('F_Cu', pcbnew.F_Cu), ('Edge_Cuts', pcbnew.Edge_Cuts)):
        pc.SetLayer(lay); pc.OpenPlotfile(name, pcbnew.PLOT_FORMAT_GERBER, name); pc.PlotLayer()
    pc.ClosePlot()
    w = pcbnew.EXCELLON_WRITER(b); w.SetFormat(True); w.SetOptions(False, False, pcbnew.VECTOR2I(0, 0), False); w.CreateDrillandMapFilesSet(outdir, True, False)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('out'); ap.add_argument('--width', type=float, default=0.5)
    ap.add_argument('--plated', action='store_true'); ap.add_argument('--gerber')
    a = ap.parse_args(); b, n = build(a.csv, a.out, a.width, plated=a.plated)
    if a.gerber: gerbers(b, a.gerber)
    print('Готово:', n)
