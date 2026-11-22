"""Audition: breaks from the pack, each retriggered every bar at the song's tempo (134 BPM, speed 6)."""
import mod
m = mod.Module("break test")
cands = [("ST-38/break004", "B-2"), ("ST-38/break007", "B-2"), ("ST-38/break001", "D-2"), ("ST-34/break8", "E-2")]
ss = [m.sample(p) for p, _ in cands]
for (p, note), s in zip(cands, ss):
    pat = m.pattern()
    for bar in range(4):
        pat.put(bar * 16, 0, note, s)
        pat.put(bar * 16, 1, note, s)          # both sides: centre
    if pat.index == 0:
        pat.put(0, 2, None, None, "F06")
        pat.put(0, 3, None, None, "F86")       # 134 BPM
m.order = [p.index for p in m.patterns]
m.write("out/break_test.mod")
print(mod.render("out/break_test.mod", "out/break_test.mp3"))
