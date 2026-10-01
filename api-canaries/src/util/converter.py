def convert_string_to_number(s: str) -> int:
    s = s.strip()
    if s.endswith("K") or s.endswith("k"):
        return int(float(s[:-1]) * 1_000)
    elif s.endswith("M") or s.endswith("m"):
        return int(float(s[:-1]) * 1_000_000)
    else:
        return int(s)
