import csv
import re
import json
from pathlib import Path
from difflib import SequenceMatcher

FIELDS = ("registration_id", "person_id", "full_name", "email", "phone", "event_name")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE = re.compile(r"^\+?[0-9][0-9\s-]{6,15}$")

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def validate_record(r):
    e = []
    for k in FIELDS:
        if not str(r.get(k, "") or "").strip():
            e.append("missing_" + k)
    email = str(r.get("email", "") or "").strip()
    phone = str(r.get("phone", "") or "").strip()
    if email and not EMAIL.match(email):
        e.append("invalid_email")
    if phone and not PHONE.match(phone):
        e.append("invalid_phone")
    return e

def norm(v):
    return re.sub(r"\s+", " ", str(v or "").strip().lower())

def is_similar_name(n1, n2):
    """
    Identifies true typographical errors between two attendee names.
    Does NOT flag distinct people who merely share a surname
    (e.g., 'Charan Subramanian' vs 'Dharun Subramanian', 'Hari Suresh' vs 'Harini Suresh').
    """
    n1 = norm(n1)
    n2 = norm(n2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return False  # Handled by exact repeated_full_name

    parts1 = n1.split()
    parts2 = n2.split()

    if len(parts1) >= 2 and len(parts2) >= 2:
        first1, last1 = parts1[0], " ".join(parts1[1:])
        first2, last2 = parts2[0], " ".join(parts2[1:])

        # Surnames must be identical or very close typo
        r_last = SequenceMatcher(None, last1, last2).ratio()
        if r_last < 0.88:
            return False

        # First names length difference cannot exceed 1 character
        if abs(len(first1) - len(first2)) > 1:
            return False

        # First names must be orthographically close (e.g. Priya vs Priyaa, Karthik vs Kartik)
        r_first = SequenceMatcher(None, first1, first2).ratio()
        if r_first < 0.80:
            return False

        # Overall full name must be a close match
        r_full = SequenceMatcher(None, n1, n2).ratio()
        return r_full >= 0.90
    else:
        return SequenceMatcher(None, n1, n2).ratio() >= 0.92

def analyse_records(records, threshold=0.90):
    invalid = []
    valid = []
    for orig in records:
        r = {k: ("" if v is None else str(v).strip()) for k, v in orig.items()}
        issues = validate_record(r)
        r["validation_issues"] = ";".join(issues)
        if issues:
            invalid.append(r)
        else:
            valid.append(r)

    flags = set()
    reasons = {}

    pid_map = {}
    email_map = {}
    name_map = {}
    phone_map = {}

    for i, r in enumerate(valid):
        pid = norm(r.get("person_id"))
        em = norm(r.get("email"))
        nm = norm(r.get("full_name"))
        ph = norm(r.get("phone"))

        if pid:
            if pid in pid_map:
                for prev_i in pid_map[pid]:
                    flags.update((i, prev_i))
                    reasons.setdefault(i, set()).add("repeated_person_id")
                    reasons.setdefault(prev_i, set()).add("repeated_person_id")
                pid_map[pid].append(i)
            else:
                pid_map[pid] = [i]

        if em:
            if em in email_map:
                for prev_i in email_map[em]:
                    flags.update((i, prev_i))
                    reasons.setdefault(i, set()).add("repeated_email")
                    reasons.setdefault(prev_i, set()).add("repeated_email")
                email_map[em].append(i)
            else:
                email_map[em] = [i]

        if nm:
            if nm in name_map:
                for prev_i in name_map[nm]:
                    flags.update((i, prev_i))
                    reasons.setdefault(i, set()).add("repeated_full_name")
                    reasons.setdefault(prev_i, set()).add("repeated_full_name")
                name_map[nm].append(i)
            else:
                name_map[nm] = [i]

        if ph:
            if ph in phone_map:
                for prev_i in phone_map[ph]:
                    flags.update((i, prev_i))
                    reasons.setdefault(i, set()).add("repeated_phone")
                    reasons.setdefault(prev_i, set()).add("repeated_phone")
                phone_map[ph].append(i)
            else:
                phone_map[ph] = [i]

    # Similar Name Matching using windowing for scale
    names = [norm(r.get("full_name")) for r in valid]
    pairs = 0

    if len(valid) <= 300:
        for i in range(len(valid)):
            ni = names[i]
            if not ni:
                continue
            for j in range(i):
                nj = names[j]
                if not nj:
                    continue
                if is_similar_name(ni, nj):
                    pairs += 1
                    flags.update((i, j))
                    reasons.setdefault(i, set()).add(f"similar_name_candidate:{j}")
                    reasons.setdefault(j, set()).add(f"similar_name_candidate:{i}")
    else:
        sorted_indices = sorted(range(len(valid)), key=lambda idx: names[idx])
        window_size = 20
        for pos in range(len(sorted_indices)):
            i = sorted_indices[pos]
            ni = names[i]
            if not ni:
                continue
            for k in range(pos + 1, min(pos + window_size, len(sorted_indices))):
                j = sorted_indices[k]
                nj = names[j]
                if not nj:
                    continue
                if is_similar_name(ni, nj):
                    pairs += 1
                    flags.update((i, j))
                    reasons.setdefault(i, set()).add(f"similar_name_candidate:{j}")
                    reasons.setdefault(j, set()).add(f"similar_name_candidate:{i}")

    clean = []
    review = []
    for i, r in enumerate(valid):
        if i in flags:
            x = dict(r)
            x["review_reason"] = ";".join(sorted(reasons.get(i, set())))
            review.append(x)
        else:
            clean.append(r)

    # Event breakdown
    event_stats = {}
    for r in records:
        ev = (r.get("event_name") or "").strip() or "Unassigned"
        if ev not in event_stats:
            event_stats[ev] = {"total": 0, "clean": 0, "review": 0, "invalid": 0}
        event_stats[ev]["total"] += 1
    for r in clean:
        ev = (r.get("event_name") or "").strip() or "Unassigned"
        if ev in event_stats:
            event_stats[ev]["clean"] += 1
    for r in review:
        ev = (r.get("event_name") or "").strip() or "Unassigned"
        if ev in event_stats:
            event_stats[ev]["review"] += 1
    for r in invalid:
        ev = (r.get("event_name") or "").strip() or "Unassigned"
        if ev in event_stats:
            event_stats[ev]["invalid"] += 1
    for ev, st in event_stats.items():
        st["clean_rate"] = round((st["clean"] / st["total"]) * 100, 1) if st["total"] else 0

    # Issues breakdown
    issues_counts = {}
    for r in invalid:
        for iss in (r.get("validation_issues") or "").split(";"):
            if iss:
                issues_counts[iss] = issues_counts.get(iss, 0) + 1
    for r in review:
        for rsn in (r.get("review_reason") or "").split(";"):
            if rsn:
                key = "similar_name_match" if rsn.startswith("similar_name_candidate") else rsn
                issues_counts[key] = issues_counts.get(key, 0) + 1

    total_n = len(records)
    clean_n = len(clean)
    inv_n = len(invalid)
    rev_n = len(review)

    missing_count = sum(v for k, v in issues_counts.items() if k.startswith("missing_"))
    completeness_score = round(((total_n - missing_count) / total_n) * 100, 1) if total_n else 100
    validity_score = round(((total_n - inv_n) / total_n) * 100, 1) if total_n else 100
    uniqueness_score = round(((total_n - rev_n) / total_n) * 100, 1) if total_n else 100

    summary = {
        "total_records": total_n,
        "valid_records": len(valid),
        "invalid_records": inv_n,
        "review_records": rev_n,
        "clean_records": clean_n,
        "similar_name_pairs": pairs,
        "clean_rate": round((clean_n / total_n) * 100, 1) if total_n else 0,
        "events": event_stats,
        "issues": issues_counts,
        "dimensions": {
            "completeness": completeness_score,
            "validity": validity_score,
            "uniqueness": uniqueness_score,
            "consistency": 100.0
        },
        "readiness": {
            "badge_ready": total_n - inv_n,
            "email_ready": total_n - (issues_counts.get("missing_email", 0) + issues_counts.get("invalid_email", 0)),
            "sms_ready": total_n - (issues_counts.get("missing_phone", 0) + issues_counts.get("invalid_phone", 0)),
            "duplicate_risk": "Low" if total_n and (rev_n / total_n) < 0.1 else "Moderate"
        }
    }
    return clean, review, invalid, summary

def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else list(FIELDS)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def process_file(input_path, output_dir):
    records = read_csv(input_path)
    clean, review, invalid, summary = analyse_records(records)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "clean_records.csv", clean)
    write_csv(out / "review_list.csv", review)
    write_csv(out / "invalid_records.csv", invalid)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
