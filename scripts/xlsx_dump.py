#!/usr/bin/env python3
"""Minimal .xlsx reader (stdlib only): prints each sheet as CSV rows. Usage: xlsx_dump.py FILE [max_rows]"""
import re, sys, zipfile, xml.etree.ElementTree as ET
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
def col(ref): n = 0
def read(path):
    z = zipfile.ZipFile(path); ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS): ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml")); rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    for sh in wb.find("m:sheets", NS):
        rid = sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"); t = target[rid].lstrip("/"); t = t if t.startswith("xl/") else "xl/" + t
        rows = []
        for r in ET.fromstring(z.read(t)).iter("{%s}row" % NS["m"]):
            vals = {}
            for c in r.findall("m:c", NS):
                ref = re.match(r"([A-Z]+)", c.get("r")).group(1); idx = 0
                for ch in ref: idx = idx * 26 + ord(ch) - 64
                v = c.find("m:v", NS); isv = c.find("m:is", NS)
                val = ss[int(v.text)] if c.get("t") == "s" and v is not None else (v.text if v is not None else ("".join(x.text or "" for x in isv.iter("{%s}t" % NS["m"])) if isv is not None else ""))
                vals[idx - 1] = val
            rows.append([vals.get(i, "") for i in range(max(vals) + 1)] if vals else [])
        yield sh.get("name"), rows
if __name__ == "__main__":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
    for name, rows in read(sys.argv[1]):
        print(f"### SHEET {name} ({len(rows)} rows)")
        for r in rows[:n]: print(",".join(str(x).replace(",", ";") for x in r))
