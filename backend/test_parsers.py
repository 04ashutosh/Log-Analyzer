"""Quick smoke test for plaintext + JSON parsers."""
from parsers.plaintext_parser import PlaintextParser
from parsers.json_parser import JsonParser

# ── Plaintext ────────────────────────────────────────────────────────────────
p = PlaintextParser()
r = p.parse("[2024-01-15 10:23:45] ERROR auth-service - Connection refused")
assert r, "PlaintextParser returned empty list"
assert r[0].level.value == "ERROR",   f"Expected ERROR, got {r[0].level}"
assert r[0].service == "auth-service", f"Expected auth-service, got {r[0].service}"
assert "Connection refused" in r[0].message
print("Plaintext ✓", r[0].level, "|", r[0].service, "|", r[0].message)

# ── JSON ─────────────────────────────────────────────────────────────────────
j = JsonParser()
line = '{"level":"ERROR","service":"db","message":"Pool exhausted"}'
r2 = j.parse(line)
assert r2, "JsonParser returned empty list"
assert r2[0].level.value == "ERROR",  f"Expected ERROR, got {r2[0].level}"
assert r2[0].service == "db",        f"Expected db, got {r2[0].service}"
assert "Pool exhausted" in r2[0].message
print("JSON      ✓", r2[0].level, "|", r2[0].service, "|", r2[0].message)

# ── Malformed JSON handled gracefully ────────────────────────────────────────
r3 = j.parse("this is not json at all {{{")
assert r3[0].is_malformed is True, "Malformed line should be flagged"
print("Malformed ✓ handled gracefully, is_malformed =", r3[0].is_malformed)

print("\nAll parsers OK!")
