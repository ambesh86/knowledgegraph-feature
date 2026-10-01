import sys; sys.path.insert(0, ".")
import metrics as M

fails = []
def check(name, got, want, tol=1e-3):
    ok = abs(got - want) <= tol
    print(f"  {'OK  ' if ok else 'FAIL'} {name}: got {got:.4f} want {want:.4f}")
    if not ok: fails.append(name)

print("Wilson interval vs published values")
# Textbook: p̂=0.5, n=100, 95% → (0.4038, 0.5962)
w = M.wilson(50, 100); check("p=.5 n=100 low", w.low, 0.4038); check("p=.5 n=100 high", w.high, 0.5962)
# Wilson for 9/10 at 95% is (0.5958, 0.9821)
w = M.wilson(9, 10); check("9/10 low", w.low, 0.5958); check("9/10 high", w.high, 0.9821)

print("\nThe degenerate cases the normal approximation gets wrong")
w = M.wilson(46, 46); print(f"  46/46 → {w.format()}")
assert w.high == 1.0 and w.low < 1.0, "perfect score must not claim a zero-width interval"
w = M.wilson(0, 46);  print(f"   0/46 → {w.format()}")
assert w.low == 0.0 and w.high > 0.0
w = M.wilson(36, 46); print(f"  36/46 → {w.format()}   (the harness's current headline)")

print("\nSample size planning")
n = M.sample_size_for_margin(0.05); check("n for ±5pp", n, 385, tol=1)
n = M.sample_size_for_margin(0.10); check("n for ±10pp", n, 97, tol=1)

print("\nMcNemar exact test")
# 4 discordant, all favouring A: two-sided exact p = 2*(1/16) = 0.125 → not significant
a = [True]*4 + [True]*20 + [False]*5
b = [False]*4 + [True]*20 + [False]*5
r = M.mcnemar(a, b); check("4-0 discordant p", r.p_value, 0.125)
assert not r.significant
print(f"       {r.note}")
# 10 vs 0 discordant: p = 2*(1/1024) ≈ 0.00195 → significant
a = [True]*10 + [True]*20; b = [False]*10 + [True]*20
r = M.mcnemar(a, b); check("10-0 discordant p", r.p_value, 0.001953)
assert r.significant
print(f"       {r.note}")
# identical systems
r = M.mcnemar([True,False,True], [True,False,True]); check("identical p", r.p_value, 1.0)

print("\nCalibration (ECE)")
# perfectly calibrated: conf 0.9 on 10 items, 9 correct
c = M.calibration([0.9]*10, [True]*9 + [False]); check("perfect ECE", c.ece, 0.0)
# always says 0.99, right half the time → ECE ≈ 0.49
c = M.calibration([0.99]*10, [True]*5 + [False]*5); check("overconfident ECE", c.ece, 0.49)
assert c.bins[0]["gap"] > 0, "overconfidence must show as a positive gap"
c = M.calibration([1.0]*4, [True]*4); check("conf=1.0 counted", c.ece, 0.0)
assert c.bins and c.bins[0]["n"] == 4, "confidence exactly 1.0 must land in a bin"

print("\nCohen's kappa")
# a judge that always says True on a 90%-correct set has learned nothing
k = M.cohen_kappa([True]*9 + [False], [True]*10); check("degenerate judge kappa", k, 0.0)
k = M.cohen_kappa([True]*5 + [False]*5, [True]*5 + [False]*5); check("perfect kappa", k, 1.0)
k = M.cohen_kappa([True]*5 + [False]*5, [False]*5 + [True]*5); check("inverted kappa", k, -1.0)

print("\nBootstrap")
p, lo, hi = M.bootstrap_ci([1.0]*30 + [0.0]*10)
print(f"  mean {p:.3f}  CI {lo:.3f}–{hi:.3f}")
assert lo < p < hi
p2, lo2, hi2 = M.bootstrap_ci([1.0]*30 + [0.0]*10)
assert (lo, hi) == (lo2, hi2), "bootstrap must be reproducible"
print("  OK   reproducible across runs (seeded)")

print("\n" + ("ALL PASS" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
