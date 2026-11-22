import cadquery as cq, math, os
OUT = os.path.dirname(os.path.abspath(__file__)) + "/stl"
os.makedirs(OUT, exist_ok=True)

def save(wp, name):
    cq.exporters.export(wp, f"{OUT}/{name}.stl", tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(wp, f"{OUT}/{name}.step")

# 1. Кронштейн полки 80x60, толщина 5, ребро, 2+2 отверстия под саморез 4 мм с зенковкой
t = 5
br = (cq.Workplane("XY").polyline([(0,0),(80,0),(80,t),(t,t),(t,60),(0,60)]).close().extrude(30))
rib = (cq.Workplane("XY").polyline([(t,t),(50,t),(t,45)]).close().extrude(4).translate((0,0,13)))
br = br.union(rib).edges("|Z").fillet(1.0)
for x in (25, 65):
    br = br.cut(cq.Workplane("XZ").center(x, 9).circle(2.2).extrude(-t))
    br = br.cut(cq.Solid.makeCone(4.4, 2.2, 2.2, pnt=cq.Vector(x, t, 9), dir=cq.Vector(0,-1,0)))
    br = br.cut(cq.Workplane("XZ").center(x, 21).circle(2.2).extrude(-t))
    br = br.cut(cq.Solid.makeCone(4.4, 2.2, 2.2, pnt=cq.Vector(x, t, 21), dir=cq.Vector(0,-1,0)))
for y in (30, 52):
    for z in (9, 21):
        br = br.cut(cq.Workplane("YZ").center(y, z).circle(2.2).extrude(t))
        br = br.cut(cq.Solid.makeCone(4.4, 2.2, 2.2, pnt=cq.Vector(t, y, z), dir=cq.Vector(-1,0,0)))
save(br, "1_kronshtein")

# 2. Заглушка в профильную трубу 25x25 (стенка 1.5): юбка 25x25x3 + вставка с ламелями
cap = cq.Workplane("XY").rect(25, 25).extrude(3).edges("|Z").fillet(2).faces(">Z").edges().fillet(0.0001) if False else cq.Workplane("XY").rect(25,25).extrude(3).edges("|Z").fillet(2.5).faces("<Z").edges().fillet(1.2)
ins = cq.Workplane("XY").workplane(offset=3).rect(21.6, 21.6).extrude(12).edges("|Z").fillet(1.5)
ins = ins.cut(cq.Workplane("XY").workplane(offset=3).rect(17.6, 17.6).extrude(12).edges("|Z").fillet(1))
for z in (6, 9.5, 13):
    fin = cq.Workplane("XY").workplane(offset=z).rect(22.4, 22.4).extrude(0.8).edges("|Z").fillet(1.5)
    fin = fin.cut(cq.Workplane("XY").workplane(offset=z).rect(19, 19).extrude(0.8))
    ins = ins.union(fin)
cap = cap.union(ins)
save(cap, "2_zaglushka")

# 3. Шестерня m=1, z=32, ширина 8, ступица 14 с D-валом 6 мм (лыска 0.5)
m, z, w = 1.0, 32, 8
rp = m*z/2; ra = rp + m; rf = rp - 1.25*m; rb = rp*math.cos(math.radians(20))
def inv(r):
    a = math.sqrt(max(r*r - rb*rb, 0))/rb
    return a - math.atan(a)
half = math.pi/(2*z) + inv(rp)
pts = []
for i in range(z):
    c = 2*math.pi*i/z
    prof = []
    for k in range(9):
        r = max(rb, rf) + (ra - max(rb, rf))*k/8
        prof.append((r, half - inv(r)))
    side1 = [(r*math.cos(c - a), r*math.sin(c - a)) for r, a in prof]
    side2 = [(r*math.cos(c + a), r*math.sin(c + a)) for r, a in reversed(prof)]
    pr = c - math.pi/z
    pts.append((rf*math.cos(pr + 0.02), rf*math.sin(pr + 0.02)))
    pts += side1 + side2
gear = cq.Workplane("XY").polyline(pts).close().extrude(w)
gear = gear.cut(cq.Workplane("XY").circle(rf - 3).extrude(w).cut(cq.Workplane("XY").circle(9).extrude(w)).translate((0,0,2.5)).union(cq.Workplane("XY").workplane(offset=w-0.01).circle(1).extrude(0.01)) if False else
               cq.Workplane("XY").workplane(offset=5.5).circle(rf - 2.5).circle(9).extrude(2.5))
gear = gear.union(cq.Workplane("XY").circle(7).extrude(14))
shaft = cq.Workplane("XY").circle(3.1).extrude(14).cut(cq.Workplane("XY").center(3.1 - 0.5 + 2, 0).rect(4, 8).extrude(14))
gear = gear.cut(shaft)
for i in range(5):
    a = 2*math.pi*i/5
    gear = gear.cut(cq.Workplane("XY").center(11.5*math.cos(a), 11.5*math.sin(a)).circle(2.3).extrude(w))
save(gear, "3_shesternya")

# 4. Корпус под ESP32 DevKit (55x28): короб 64x36x22, стенка 2, вырез USB, вентиляция, стойки
L, W, H, s = 64, 36, 22, 2
box = cq.Workplane("XY").box(L, W, H, centered=(True, True, False)).edges("|Z").fillet(3).faces(">Z").shell(-s)
box = box.cut(cq.Workplane("YZ", origin=(-L/2, 0, 0)).center(0, 6.5).rect(10, 5).extrude(s*2, both=True).edges("|X").fillet(1))
for i in range(6):
    box = box.cut(cq.Workplane("XZ", origin=(0, W/2, 0)).center(-12 + i*5, 13).rect(2, 9).extrude(s*2, both=True))
for x in (-25, 25):
    for y in (-11.5, 11.5):
        box = box.union(cq.Workplane("XY").workplane(offset=s).center(x, y).circle(2.5).extrude(4).faces(">Z").workplane().hole(1.8))
lid = (cq.Workplane("XY").box(L, W, 2, centered=(True, True, False)).edges("|Z").fillet(3)
       .union(cq.Workplane("XY").workplane(offset=-2).rect(L - 2*s - 0.4, W - 2*s - 0.4).extrude(2).cut(
              cq.Workplane("XY").workplane(offset=-2).rect(L - 2*s - 3.4, W - 2*s - 3.4).extrude(2))))
lid = lid.cut(cq.Workplane("XY").center(18, 0).circle(2.6).extrude(2))
save(box, "4_korpus"); save(lid, "4_kryshka")

# 5. Клипса на трубу 20 мм с ушком под саморез
r_in, wall, wd = 10.15, 2.6, 12
clip = cq.Workplane("XY").circle(r_in + wall).circle(r_in).extrude(wd)
clip = clip.cut(cq.Workplane("XY").polyline([(0,0),(30*math.cos(math.radians(55)),30*math.sin(math.radians(55))),(-30*math.cos(math.radians(55)),30*math.sin(math.radians(55)))]).close().extrude(wd).translate((0, 2, 0)))
foot = cq.Workplane("XY").center(0, -(r_in + wall + 2)).rect(36, 4).extrude(wd).edges("|Z").fillet(1.5)
web = cq.Workplane("XY").center(0, -(r_in + 1.5)).rect(14, 5).extrude(wd)
clip = clip.union(foot).union(web)
for x in (-13, 13):
    clip = clip.cut(cq.Workplane("XZ", origin=(0, -(r_in + wall), 0)).center(x, wd/2).circle(2.1).extrude(10))
for sgn in (-1, 1):
    a = math.radians(90 - 35)*sgn
    clip = clip.union(cq.Workplane("XY").center(sgn*(r_in + wall/2)*math.cos(math.radians(55)), (r_in + wall/2)*math.sin(math.radians(55))).circle(wall/2 + 0.3).extrude(wd))
save(clip, "5_klipsa")
print("ok")
