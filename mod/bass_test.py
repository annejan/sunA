"""Audition: rave basses from the pack over break004, a bassline in A minor (Am / F G), two bars each."""
import mod

BASSES = [("ST-01/TechBass", 0), ("ST-01/MonsterBass", 0), ("ST-01/FilterBass", 0), ("ST-01/KorgBass", 0),
          ("ST-01/SyntheBass", 0), ("ST-02/HitBass", 0), ("ST-42/basshit", -6)]
# two bars, a token a row: a note, or "." (16 rows a bar)
LINE = ("A-1 . . A-1 . . A-2 . A-1 . A-1 A-2 . A-1 G-1 . "
        "F-1 . . F-1 . . F-2 . G-1 . . G-1 . G-2 E-1 G-1").split()


def shift(note, st):
    return mod.note_name(mod.note_index(note) + st)


m = mod.Module("bass test")
brk = m.sample("ST-38/break004")
bs = [m.sample(p) for p, _ in BASSES]
for i, ((p, st), b) in enumerate(zip(BASSES, bs)):
    pat = m.pattern()
    for bar in range(4):
        pat.put(bar * 16, 0, "B-2", brk)
    for r in range(64):
        tok = LINE[r % 32]
        if tok != ".":
            pat.put(r, 1, shift(tok, st + 12), b)      # an octave up: C-1 is the lowest note
    if i == 0:
        pat.put(0, 2, None, None, "F06")
        pat.put(0, 3, None, None, "F86")
m.order = [p.index for p in m.patterns]
m.write("out/bass_test.mod")
print(mod.render("out/bass_test.mod", "out/bass_test.mp3"))
