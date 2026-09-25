#!/usr/bin/env python3
"""
Refresh the Sprint 22 Validation Readiness dashboard from the ADO CSV export.

The dashboard HTML embeds a single source-of-truth JS array (`const rawItems = [...]`)
that every table, chart and KPI derives from. This script regenerates ONLY that array
(and the "data last extracted" notice) from the CSV, leaving all layout/logic untouched.

Usage:  python3 build_validation_readiness_html.py
"""
import csv
import os
import re
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "OM&eB2B - Release 6 - Sprint 23.csv")
HTML_TARGETS = [
    os.path.join(HERE, "Sprint_Validation_Readiness.html"),
    os.path.join(HERE, "index.html"),  # deployed copy, kept in sync
]


def first_name(assigned_to):
    """'Claquesin, Aude (Contractor) <aude.claquesin@effem.com>' -> 'Aude'."""
    s = (assigned_to or "").strip()
    if not s or "," not in s:
        return ""
    after = s.split(",", 1)[1].strip()
    # cut at the first '(' (role) or '<' (email)
    after = re.split(r"[(<]", after, 1)[0].strip()
    return after


def to_int(v):
    v = (v or "").strip()
    try:
        return int(float(v))
    except ValueError:
        return 0


def js_str(s):
    """Escape a Python string for a JS double-quoted literal."""
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def split_tags(tags):
    return [t.strip() for t in (tags or "").split(";") if t.strip()]


def build_raw_items():
    lines = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            item = {
                "id": (row["ID"] or "").strip(),
                "title": (row["Title"] or "").strip(),
                "assignee": first_name(row["Assigned To"]),
                "state": (row["State"] or "").strip(),
                "tags": split_tags(row["Tags"]),
                "ux_ui": to_int(row["UX UI Related"]),
                "data_rel": to_int(row["Data Related"]),
                "t": to_int(row["Technical Validation"]),
                "u": to_int(row["UX Validation"]),
                "d": to_int(row["Data validation"]),
                "b": to_int(row["Business Validation"]),
                "sp": to_int(row["Story Points"]),
                "parent": (row["Parent"] or "").strip(),
            }
            tags_js = "[" + ",".join('"%s"' % js_str(t) for t in item["tags"]) + "]"
            lines.append(
                '            {id:"%s",title:"%s",assignee:"%s",state:"%s",tags:%s,'
                'ux_ui:%d,data_rel:%d,t:%d,u:%d,d:%d,b:%d,sp:%d,parent:"%s"}'
                % (
                    item["id"], js_str(item["title"]), js_str(item["assignee"]),
                    js_str(item["state"]), tags_js, item["ux_ui"], item["data_rel"],
                    item["t"], item["u"], item["d"], item["b"], item["sp"], item["parent"],
                )
            )
    return ",\n".join(lines), len(lines)


def main():
    raw_block, n = build_raw_items()

    # "data last extracted" timestamp = CSV file modification time
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(CSV_PATH))
    extracted = mtime.strftime("%B %-d, %Y at %-I:%M %p CEST")

    new_array = (
        "        const rawItems = [\n"
        + raw_block
        + "\n        ];"
    )

    array_re = re.compile(r"        const rawItems = \[.*?\n        \];", re.DOTALL)
    notice_re = re.compile(
        r"(ADO data last extracted on <strong>)[^<]*(</strong>)"
    )

    for path in HTML_TARGETS:
        with open(path, encoding="utf-8") as f:
            html = f.read()
        if not array_re.search(html):
            raise SystemExit("Could not locate rawItems array in %s" % path)
        html = array_re.sub(lambda m: new_array, html, count=1)
        html = notice_re.sub(r"\g<1>%s\g<2>" % extracted, html, count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("Updated %s" % os.path.basename(path))

    print("Wrote %d work items. Extraction timestamp: %s" % (n, extracted))


if __name__ == "__main__":
    main()
