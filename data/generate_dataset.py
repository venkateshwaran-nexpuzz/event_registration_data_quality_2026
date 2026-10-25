#!/usr/bin/env python3
"""
G11 DataWise — High-Performance Dataset Generator
Generates realistic, scalable event registration datasets (320 to 10,000+ records)
with configurable, exact data quality anomalies (duplicates, missing fields, invalid formats, similar typo names).
"""

import sys
import random
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from src.g11_tool import write_csv, process_file  # type: ignore # noqa: E402
except ImportError:
    from g11_tool import write_csv, process_file  # type: ignore # noqa: E402

FIRST_NAMES = [
    "Aarav", "Priya", "Rahul", "Ananya", "Vikram", "Deepika", "Karthik", "Kavya",
    "Suresh", "Divya", "Sanjay", "Meera", "Rohan", "Sneha", "Harish", "Lakshmi",
    "Arun", "Pooja", "Manoj", "Swathi", "Aditya", "Nila", "Varun", "Bhavna",
    "Gautam", "Shreya", "Amit", "Geetha", "Naveen", "Tanvi", "Manish", "Ishaan",
    "Jaya", "Charan", "Harini", "Iniya", "Jeeva", "Kavin", "Keerthana", "Lavanya",
    "Madhan", "Monisha", "Pranav", "Rithika", "Surya", "Yazhini", "Vignesh", "Dinesh",
    "Farhan", "Zoya", "Chetan", "Bhuvan", "Abinaya", "Vijay", "Aishwarya", "Bharath",
    "Anand", "Akash", "Anu", "Balaji", "Chitra", "Deepak", "Devi", "Eswar",
    "Gayathri", "Gopinath", "Hema", "Indra", "Janani", "Kamal", "Kalyani", "Kishore",
    "Latha", "Mahesh", "Nandini", "Padma", "Parth", "Preeti", "Radha", "Rajesh",
    "Ramesh", "Revathi", "Sangeetha", "Saravanan", "Sathish", "Shankar", "Shobana", "Sindhu",
    "Sridhar", "Subha", "Sundar", "Usha", "Vasanth", "Vidya", "Vinoth", "Yuvan"
]

LAST_NAMES = [
    "Kumar", "Sharma", "Patel", "Iyer", "Nair", "Balan", "Mohan", "Rao",
    "Singh", "Reddy", "Verma", "Menon", "Pillai", "Gowda", "Das", "Gupta",
    "Joshi", "Bose", "Chopra", "Sen", "Dutta", "Bhat", "Kaur", "Agrawal",
    "Fernandes", "Hegde", "Iyengar", "Kulkarni", "Mahajan", "Nadkarni", "Shetty",
    "Trivedi", "Upadhyay", "Venkatesh", "Wadhwa", "Yadav", "Banerjee", "Chatterjee",
    "Mukherjee", "Deshmukh", "Suresh", "Prakash", "Mani", "Natarajan", "Selvan",
    "Raman", "Krishnan", "Subramanian", "Murugan", "Kannan", "Anand", "Devi",
    "Babu", "Chander", "Ganesan", "Jayaraman", "Kailash", "Madhavan", "Narayanan", "Pandian",
    "Raghavan", "Rajendran", "Sampath", "Srinivasan", "Thakur", "Vaidya", "Varadhan", "Vohra"
]

EVENT_TRACKS = [
    "Python Workshop",
    "AI Seminar",
    "Data Science Bootcamp",
    "Cybersecurity Talk",
    "Cloud Computing",
    "Tech Symposium",
    "Full-Stack Dev Summit",
    "DevOps Masterclass"
]

def generate_dataset(total_count=3000, seed=42):
    random.seed(seed)

    # 1. Generate unique combinations of full names to avoid unintentional collisions
    combos = [(f, l) for f in FIRST_NAMES for l in LAST_NAMES]
    random.shuffle(combos)

    if total_count > len(combos):
        middle_initials = ["A.", "B.", "C.", "D.", "E.", "K.", "M.", "N.", "P.", "R.", "S.", "T.", "V."]
        extended = [(f, f"{m} {l}") for f in FIRST_NAMES for l in LAST_NAMES for m in middle_initials]
        random.shuffle(extended)
        combos.extend(extended)

    records = []
    for i in range(1, total_count + 1):
        fn, ln = combos[(i - 1) % len(combos)]
        name = f"{fn} {ln}"
        pid = f"P{i:05d}"
        rid = f"REG{i:05d}"
        clean_ln = ln.replace(" ", "").replace(".", "").lower()
        clean_email = f"{fn.lower()}.{clean_ln}{i}@example.com"
        phone = f"9{random.randint(100000000, 999999999)}"
        ev = EVENT_TRACKS[(i - 1) % len(EVENT_TRACKS)]

        records.append({
            "registration_id": rid,
            "person_id": pid,
            "full_name": name,
            "email": clean_email,
            "phone": phone,
            "event_name": ev
        })

    # Total invalid target: ~2.0%
    invalid_target = max(6, int(total_count * 0.02))
    miss_name_cnt = max(2, invalid_target // 3)
    inv_email_cnt = max(2, invalid_target // 3)
    inv_phone_cnt = invalid_target - miss_name_cnt - inv_email_cnt

    used_indices = set()

    # 1. Missing full names
    for _ in range(miss_name_cnt):
        idx = random.choice([x for x in range(total_count) if x not in used_indices])
        records[idx]["full_name"] = ""
        used_indices.add(idx)

    # 2. Invalid email format
    bad_emails = ["not-an-email", "missing-at-sign.com", "user@nodomain", "space in@email.com", "@example.com", "vijay.example.com"]
    for _ in range(inv_email_cnt):
        idx = random.choice([x for x in range(total_count) if x not in used_indices])
        records[idx]["email"] = random.choice(bad_emails)
        used_indices.add(idx)

    # 3. Invalid phone format
    bad_phones = ["12345", "123", "+000", "99999"]
    for _ in range(inv_phone_cnt):
        idx = random.choice([x for x in range(total_count) if x not in used_indices])
        records[idx]["phone"] = random.choice(bad_phones)
        used_indices.add(idx)

    # Target Review records: ~2.5% to 3.0% (split between duplicate identities and subtle typo pairs)
    review_pairs = max(3, int(total_count * 0.0125))
    clean_pool = [x for x in range(total_count) if x not in used_indices]
    random.shuffle(clean_pool)

    # A. Repeated email pairs (different registrant, shared contact email)
    for _ in range(review_pairs // 3):
        if len(clean_pool) < 2:
            break
        src = clean_pool.pop()
        tgt = clean_pool.pop()
        records[tgt]["email"] = records[src]["email"]

    # B. Repeated full name pairs (same person registered twice)
    for _ in range(review_pairs // 3):
        if len(clean_pool) < 2:
            break
        src = clean_pool.pop()
        tgt = clean_pool.pop()
        records[tgt]["full_name"] = records[src]["full_name"]

    # C. Typo name pairs (human review candidates, e.g. Priya Sharma vs Priya Sharmaa)
    while len(clean_pool) >= 2 and review_pairs > 0:
        src = clean_pool.pop()
        tgt = clean_pool.pop()
        base_name = records[src]["full_name"]
        parts = base_name.split()
        if len(parts) >= 2:
            records[tgt]["full_name"] = f"{parts[0]} {parts[1]}{parts[1][-1]}"
        else:
            records[tgt]["full_name"] = f"{base_name}{base_name[-1]}"
        review_pairs -= 1

    return records

def main():
    parser = argparse.ArgumentParser(description="Generate scalable event registration datasets")
    parser.add_argument("count", nargs="?", type=int, default=3000, help="Total records to generate (default: 3000)")
    parser.add_argument("--save-copy", action="store_true", help="Also save a permanent copy in data/")
    args = parser.parse_args()

    count = args.count
    data_dir = ROOT / "data"
    out_dir = ROOT / "outputs"
    data_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)

    dest_file = data_dir / "registrations.csv"

    # If count is 320 and backup exists, use the authentic 320 records
    if count == 320 and (data_dir / "registrations_320_backup.csv").exists():
        print("Restoring authentic 320-record dataset...")
        records_text = (data_dir / "registrations_320_backup.csv").read_bytes()
        dest_file.write_bytes(records_text)
    else:
        print(f"Generating {count:,} high-quality event registration records...")
        records = generate_dataset(total_count=count)
        write_csv(dest_file, records)
        print(f"Saved {count:,} records to {dest_file}")

        if args.save_copy or count >= 1000:
            copy_file = data_dir / f"registrations_{count}.csv"
            write_csv(copy_file, records)
            print(f"Archived copy saved to {copy_file}")

    print("Running high-performance data quality analysis...")
    summary = process_file(dest_file, out_dir)

    print("\n--- DATA QUALITY AUDIT SUMMARY ---")
    print(f"Total Registrations:  {summary['total_records']:,}")
    print(f"Clean & Verified:     {summary['clean_records']:,} ({summary.get('clean_rate', 0)}%)")
    print(f"Review Candidates:    {summary['review_records']:,}")
    print(f"Invalid Records:      {summary['invalid_records']:,}")
    print(f"Similar Name Pairs:   {summary['similar_name_pairs']:,}")
    print(f"Event Tracks:         {len(summary.get('events', {}))}")
    print("----------------------------------\n")
    print("Ready to view at http://127.0.0.1:8000")

if __name__ == "__main__":
    main()
