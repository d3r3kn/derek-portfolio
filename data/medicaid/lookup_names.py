"""Look up names for the top billing providers in summary.json.

Uses the public CMS NPI Registry API (npiregistry.cms.hhs.gov). Writes
npi_names.json: name, entity type, practice city/state, and primary taxonomy.
"""
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
API = "https://npiregistry.cms.hhs.gov/api/?version=2.1&number={}"


def lookup(npi):
    with urllib.request.urlopen(API.format(npi), timeout=30) as resp:
        result = (json.load(resp).get("results") or [{}])[0]
    basic = result.get("basic", {})
    location = next((a for a in result.get("addresses", []) if a.get("address_purpose") == "LOCATION"), {})
    taxonomy = next((t for t in result.get("taxonomies", []) if t.get("primary")), {})
    return {
        "name": basic.get("organization_name") or " ".join(filter(None, [basic.get("first_name"), basic.get("last_name")])),
        "entity": result.get("enumeration_type"),
        "city": location.get("city"),
        "state": location.get("state"),
        "taxonomy": taxonomy.get("desc"),
    }


def main():
    summary = json.loads((HERE / "summary.json").read_text())
    npis = {p["npi"] for preset in summary["presets"].values() for p in preset["top_billing"]}
    names = {}
    for npi in sorted(npis):
        names[npi] = lookup(npi)
        print(npi, names[npi]["name"], names[npi]["state"])
        time.sleep(0.3)
    (HERE / "npi_names.json").write_text(json.dumps(names, indent=1))


if __name__ == "__main__":
    main()
