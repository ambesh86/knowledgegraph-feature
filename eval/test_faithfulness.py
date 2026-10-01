import sys, json; sys.path.insert(0, "/Users/rajeshgupta/PycharmProjects/knowledgeGraph/eval")
import faithfulness as F

# The real answer produced by the deployed system earlier today.
answer = """Emicizumab is an approved bispecific monoclonal antibody (IgG4-hetFc cLC) designed to
mimic the activity of coagulation Factor VIII by binding to Factor IXa and Factor X. It was approved
for the treatment of hemophilia A in 2017 [Evidence 5, Evidence 7].
Negrier C, Kessler C, et al. demonstrated the effectiveness of emicizumab prophylaxis in hemophilia A
patients with inhibitors (N Engl J Med. 2017;377(9):809-818) [Evidence 4].
The response rate was 62.9% in the treated arm versus 4.8% in controls [Evidence 9].
Twenty-three migs have an unmodified gamma-4 heavy chain [Evidence 12]."""

# What retrieval actually returned. Note 62.9 and 4.8 appear NOWHERE — they are
# the fabricated-statistic case this check exists to catch.
passages = [
 "Emicizumab is an approved IgG4-hetFc cLC antibody designed to mimic the activity of coagulation Factor VIII by binding Factor IXa and Factor X. Approved 2017 for hemophilia A.",
 "Negrier C, Kessler C, et al. Emicizumab prophylaxis in hemophilia A with inhibitors. N Engl J Med. 2017;377(9):809-818.",
 "The field of hematologic diseases is dominated by migs being pro-coagulants, for example targeting FIXa x FX.",
 "Twenty-three migs have an unmodified gamma-4 heavy chain or Fc part and thus have reduced Fc-mediated effector functions.",
]

r = F.evaluate(answer, passages)
d = r.as_dict()
print("NUMERIC GROUNDEDNESS  %.0f%%  (%d/%d statistics traceable to a cited passage)"
      % (d["numeric_groundedness"]*100, d["numeric_supported"], d["numeric_total"]))
for u in d["ungrounded_numbers"]:
    print(f"   FLAGGED  {u['value']:>6}  …{u['context'].strip()}…")
print("\nCITATION VALIDITY     %.0f%%   invalid: %s"
      % (d["citation_validity"]*100, d["invalid_citations"] or "none"))
print("CLAIM SUPPORT         %.0f%%  (%d/%d sentences)"
      % (d["claim_support"]*100, d["sentences_supported"], d["sentences_total"]))
print("ABSTAINED             %s" % d["abstained"])

print("\n--- checks ---")
vals = {u["value"] for u in d["ungrounded_numbers"]}
assert "62.9" in vals and "4.8" in vals, f"fabricated stats not caught: {vals}"
print("  OK  caught both fabricated statistics (62.9%, 4.8%)")
assert "2017" not in vals, "year misclassified as an unsupported finding"
print("  OK  the year 2017 not flagged as a fabricated statistic")
assert not any(v in vals for v in ("377","9","809","818")), f"bibliographic numbers flagged: {vals}"
print("  OK  journal volume/issue/pages not flagged as findings")
assert "[Evidence 12]" in d["invalid_citations"], "citation beyond the passage list not caught"
print("  OK  [Evidence 12] flagged — only 4 passages were retrieved")

# A clean answer must score 100%, or the metric is useless.
clean = "Emicizumab was approved in 2017 for hemophilia A [Evidence 1]."
c = F.evaluate(clean, passages)
assert c.numeric_groundedness == 1.0 and c.citation_validity == 1.0
print("  OK  a faithful answer scores 100%% (no false alarms)")

# Abstention detection
a = F.evaluate("I do not have evidence for that in the retrieved passages.", passages)
assert a.abstained
print("  OK  abstention detected")
print("\nALL PASS")
