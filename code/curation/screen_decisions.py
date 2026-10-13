#!/usr/bin/env python3
"""Agent B: title/abstract screening decisions for all 602 auto-passed papers.

Decisions were made by an AI system (Claude) reading every title and the abstract of every paper whose
title could plausibly meet E1-E4 (docs/ELIGIBILITY.md). Papers with accessible full text that pass E1-E4
are decided on E5-E6 from the full text, in data/curated/extractions/<PMCID>.json, which overrides the
row written here. Indices refer to data/work/abstracts.json (same order as screening.csv).

Writes data/curated/screening.csv (include, exclusion_reason, reviewer, review_date) and
data/curated/screening_log.csv (code, rationale, confidence, stage).
"""
import csv
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = json.loads((ROOT / "data/work/abstracts.json").read_text())
REVIEWER = "Claude (AI) title/abstract screen"
TODAY = "2026-10-12"

# ---- E1-E4 pass on title/abstract, full text available: decided in extraction files (E5/E6) ----
FT_CANDIDATES = [96, 186, 189, 190, 261, 335, 343, 377, 385, 420, 434, 490, 549, 263, 296, 467, 554, 558]

# ---- E1-E4 pass on title/abstract, NO accessible full text -> E6 (in scope but not retrievable) ----
NOFT_IN_SCOPE = {
    51: "LDPE photo-oxidation with TiO2-benzophenone hybrid; light source to confirm",
    67: "aromatic polymer C-H fluoroalkylation by photocatalysis (functionalisation; may not be deconstruction)",
    82: "polyolefin-TiO2 composite photocatalytic degradation",
    91: "cPPA transience by SET incl. photochemical triggering",
    127: "PEG-alt-oHC polymers cleaved at 455 nm",
    128: "PS nanoplastics degraded with CuxO under visible light",
    134: "phenoxy resin / hydroxylated polyolefins depolymerised by visible-light PCET",
    179: "microplastic upcycling over Ag2O/Fe-MOF (light-driven)",
    227: "PET-RAFT depolymerisation under visible light, stepwise Mn decrease",
    229: "PET-RAFT depolymerisation under visible light (duplicate record of 227)",
    240: "upcycling non-biodegradable plastics by base-metal photocatalysis",
    259: "thiol epoxy thermosets depolymerised by light-driven PCET",
    268: "PS aerobic photochemical upcycling with anthraquinone",
    269: "plastics reformed over ZnIn2S4 under visible light",
    273: "poly(vinyl ether) photo-oxidative degradation with visible light",
    276: "PE to ethylene/propionic acid over Pd/TiO2 photocatalyst",
    305: "acridinium PS upcycling (publisher record of PMC11796324, which is processed)",
    310: "PS aerobic upcycling, indirect HAT, 390 nm Kessil",
    313: "PS aerobic upcycling, thioxanthone/NBS, 390 nm",
    319: "vinyl ketone polymers photodegraded at 310-630 nm incl. 390/450 nm",
    321: "plastics with aliphatic C-C bonds photocatalytically upcycled",
    322: "PS on WO3 photoanode, sunlight-driven",
    331: "protocol: photocatalytic upcycling of plastics resin codes 2-7",
    337: "PET aerobic oxidation over PdCu-TiO2 in flow (light)",
    386: "PS to phenols by photocatalysis",
    435: "PE photocatalytic conversion over MXene, simulated solar",
    438: "commercial polymethacrylates depolymerised by visible light (chlorine radicals)",
    479: "ABS/microplastic mineralisation under AM1.5G with naphthalimide",
    480: "PS oxidative cleavage over fluorenone POPs, 455 nm",
    482: "PS to benzoic acid over Co single-atom PCN, white light",
    491: "PS photocracking in CH2Cl2 at 365-415 nm",
    493: "PE degradation over WO3 nanoflowers, visible light",
    495: "PS aerobic upcycling, InBr3 + Br radical source",
    507: "PET microplastic degradation over BiOCl0.5I0.5, visible light",
    508: "PS upcycling over vacancy-engineered g-C3N4",
    509: "PS upcycling over Fe-doped CTF",
    515: "PMMA copolymers depolymerised by 405 nm HAT",
    524: "PE microplastics over CuO/ferrites, visible light",
    525: "PE microplastics with tea polyphenol-hematite, light-driven",
    538: "post-consumer PS to phenol with eosin Y, blue light",
    545: "commercial polymethacrylates, photocatalytic, solvent-independent",
    557: "PMMA copolymer scission by tandem photochemical HAT/XAT",
    561: "RAFT PMMA depolymerisation with acid, green light",
    562: "catalyst-free visible-light upcycling of PS and aromatic polymers",
    565: "PET over Ag/Zr-MOF under Xe lamp",
    587: "commercial polymethacrylates, photocatalytic (duplicate record of 545)",
    593: "metal-free PCN photoredox upcycling of PP, PS, PVC etc., visible light",
    60: "microplastics photodissolved to DOC under solar simulator (endpoint likely DOC/mass loss)",
    122: "macro/microplastics, thermo-photocatalytic ZnO",
    200: "expanded PS photo-oxidised; soluble products identified",
    210: "marine microplastic photodegradation (light source unclear)",
    251: "PLA photocatalytic hydrolysis (light role to confirm)",
    511: "microplastics photodegraded with chalcopyrite/pyrite",
    445: "UHMWPE natural outdoor weathering (endpoint likely mechanical properties)",
}

# ---- Explicit exclusions with reasons (title/abstract) ----
E1_REVIEW = [14, 17, 43, 88, 125, 150, 152, 156, 171, 172, 173, 174, 178, 197, 202, 204, 220, 221, 223, 224, 225, 226, 228,
             231, 232, 235, 236, 241, 246, 272, 280, 300, 301, 304, 306, 311, 312, 314, 328, 330, 332, 338, 344, 345, 349, 351,
             353, 359, 365, 368, 370, 371, 374, 375, 378, 379, 380, 382, 389, 392, 395, 399, 403, 407, 409, 410, 411, 417, 436,
             440, 441, 442, 449, 450, 451, 452, 455, 460, 461, 462, 466, 468, 469, 473, 475, 476, 478, 484, 498, 513, 519, 528,
             536, 568, 573, 574, 585, 588, 590, 592, 594, 595, 596, 599, 53, 58, 151, 182, 257, 315, 326, 236]
E3_UV_ONLY = [295, 567, 571, 579, 169, 16, 20, 90, 108, 157, 188, 243, 271, 366, 373, 404, 529, 589, 598, 601, 503, 54, 84, 121]
E4_NO_PHOTO = [578, 517, 123, 13, 70, 99, 107, 118, 130, 139, 146, 165, 198, 201, 209, 218, 248, 256, 260, 270, 294, 308, 336, 347, 352,
               390, 416, 430, 433, 459, 464, 486, 489, 544, 546, 547, 563, 580, 581, 583, 584, 597, 140, 414, 252, 233,
               230, 318, 383, 387, 391, 398, 400, 419, 444, 481, 483, 500, 506, 510, 521, 554, 384, 388]
E4_REASONS = {130: "HNO3 oxidative depolymerisation; light step decarboxylates small acids",
              260: "enzymatic pretreatment depolymerises; photoreforming acts on monomers",
              416: "photothermal (light-to-heat) depolymerisation, not photochemical",
              544: "photothermal (light-to-heat) depolymerisation, not photochemical",
              464: "photoreforming in alkaline solution; chain cleavage by hydrolysis",
              251: "photocatalytic hydrolysis of PLA; light role ambiguous (no full text)",
              252: "PET hydrolysate (EG) photoreforming",
              233: "PET photoreforming after alkaline pretreatment", 318: "PET photoreforming in alkaline media",
              383: "PET photoreforming", 387: "PET photoreforming", 391: "PLA photoreforming after hydrolysis",
              398: "PLA photoreforming", 400: "plastic-derived lactate, not polymer", 419: "PLA to alanine via hydrolysate",
              444: "PLA photoreforming", 481: "PLA photoreforming to lactate", 483: "plastics photoreforming", 500: "PET photoreforming with CO2",
              506: "PET-derived ethylene glycol", 510: "PET-derived intermediates", 521: "PLA hydrolysate", 230: "plasma step oxidises PE; solar reforming of products",
              554: "PET microplastic photoreforming (decided at full text)",
              384: "PE C-H functionalisation (nitrosation), not deconstruction", 388: "PE C-H functionalisation (nitrosation), not deconstruction",
              486: "light only for curing; depolymerisation by DBU", 489: "light only for curing; depolymerisation by DBU",
              546: "thermal hydroperoxide depolymerisation, no light", 547: "thermal depolymerisation, no light",
              430: "thermal RAFT depolymerisation", 347: "thermal Sn-catalysed PLA depolymerisation", 433: "guanidine methanolysis"}

# ---- Re-screen after the independent audit (2026-10-12). Every E2 paper whose title or abstract mentions a
# synthetic polymer or plastics (153) and every E3 paper was re-read on its abstract; these are the changes.
# Papers not listed here keep their code. Format: index -> (code, rationale, confidence)
RESCREEN = {
    # in scope by abstract, open full text available -> decided at full text (extraction file)
    164: ("pending_fulltext", "HDPE microplastics photocatalytically degraded with C,N-TiO2", "n/a"),
    418: ("pending_fulltext", "microplastic degradation with iron vanadate photocatalysts under solar light", "n/a"),
    465: ("pending_fulltext", "photocatalytic oxidation of nanoplastics on BiOI/CuWO4 films", "n/a"),
    550: ("pending_fulltext", "LDPE/HDPE films photocatalytically degraded with ZnO/Fe3O4 under sunlight", "n/a"),
    537: ("pending_fulltext", "LDPE particles photocatalytically decomposed in a MIL-88B(Fe) membrane reactor", "n/a"),
    # in scope by abstract, no retrievable full text
    320: ("E6", "PET degraded by persistent photocatalysis with peroxymonosulfate; no retrievable full text", "medium"),
    381: ("E6", "PVC/PE/PET/PP photocatalytically upcycled to acetic acid under AM1.5G; no retrievable full text", "medium"),
    396: ("E6", "PP films degraded by solid-state TiO2/biochar photocatalysis; no retrievable full text", "medium"),
    523: ("E6", "PS microplastics degraded under visible light on Fe3O4-COF/PVDF membranes; no retrievable full text", "medium"),
    376: ("E6", "PET converted to H2 and organic acids under visible light; pretreatment not stated in abstract; no retrievable full text", "low"),
    175: ("E6", "poly(phenylacetylene)s degrade under visible light (photo-electrocyclization); no retrievable full text", "medium"),
    16: ("E6", "PMMA photo-oxidation under a xenon lamp (E3 passes: Xe without UV cut-on); no retrievable full text", "medium"),
    601: ("E6", "LLDPE photo-oxidation incl. natural rooftop weathering (sunlight); no retrievable full text", "medium"),
    295: ("E6", "PS accelerated weathering monitored by SEC; light source not stated in abstract; no retrievable full text", "low"),
    589: ("E6", "post-consumer PET under intense solar/UV radiation; light source unclear; no retrievable full text", "low"),
    # photoreforming / hydrolysis-first conventions (E4)
    397: ("E4", "plastics photoreformed to H2 after pretreatment; light acts on dissolved products", "medium"),
    518: ("E4", "PLA hydrolysed by proteinase K before photoconversion", "high"),
    # no light / not photochemical deconstruction
    93: ("E4", "PS microplastic fragmentation by agitation, not light", "high"),
    282: ("E4", "oxo-degradable additive; biodegradation measured", "medium"),
    23: ("E4", "self-immolative polymers with chemical triggers; no photochemical deconstruction stated", "medium"),
    167: ("E4", "enzymatic degradation of PLA/PAni films", "high"),
    516: ("E4", "chemical recycling of epoxy composite, no light", "high"),
    488: ("E4", "light used for photoclick polymerization; recycling is thermal", "high"),
    54: ("E4", "laser surface processing of PET, not photochemical deconstruction", "medium"),
    121: ("E4", "femtosecond laser micromachining", "high"),
    # UV-only, stated in the abstract
    106: ("E3", "UV radiation chamber among other ageing conditions", "medium"),
    443: ("E3", "UV absorption/photoreactivity of PS microplastics at 295 nm; no visible-light deconstruction", "medium"),
    44: ("E3", "accelerated weathering in a UV device", "high"),
    # reviews and non-primary items
    342: ("E1", "review", "high"), 501: ("E1", "review", "high"), 575: ("E1", "review", "high"), 275: ("E1", "review", "high"),
    401: ("E1", "review", "high"), 470: ("E1", "conceptual/analytical framework, not a deconstruction experiment", "medium"),
    474: ("E1", "review", "high"), 222: ("E1", "review", "high"), 238: ("E1", "review", "high"), 234: ("E1", "review", "high"),
    277: ("E1", "review", "high"), 494: ("E1", "review", "high"), 539: ("E1", "perspective/review", "medium"), 496: ("E1", "review", "high"),
    169: ("E1", "review of UV absorbers", "high"),
    # substrate corrections
    13: ("E2", "substrate is a biopolymer (PHA) in bacteria", "high"),
    526: ("E2", "field-sample characterization (carbonyl index, isotopes), not a deconstruction experiment", "medium"),
}
# Duplicate records of the same work (counted once, under the other index)
DUPLICATES = {149: 130, 176: 175, 229: 227, 587: 545, 305: 385, 598: 589, 487: 485}


def title_code(i, t):
    """Default for titles judged out of scope on reading (all 602 titles were read)."""
    tl = t.lower()
    if any(k in tl for k in ("lignin", "cellulos", "polysaccharid", "chitosan", "fucoidan", "xylan", "lignocellul", "biomass",
                             "suberin", "carbohydrat", "glucan", "starch", "alginate", "polyhydroxyalkano")):
        return "E2", "substrate is a biopolymer or biomass"
    if any(k in tl for k in ("dye", "methylene", "rhodamine", "pollutant", "phenol", "remazol", "malachite", "reactive black",
                             "ciprofloxacin", "antibiotic", "water treatment", "water remediation", "wastewater", "vocs",
                             "air purification", "self-cleaning", "bexarotene", "estrogen", "atrazine", "contaminant",
                             "trinitrotoluene", "oil in water", "virucidal", "biological contaminants", "acetaminophen")):
        return "E2", "substrate is a small-molecule pollutant/dye; polymer (if any) is a support or matrix"
    return "E2", "not a study of synthetic-polymer deconstruction (biology, materials synthesis/properties, or other topic)"


def main():
    rows, log = [], []
    for i, a in enumerate(A):
        has_ft = bool(a["fulltext"]) and not a["fulltext"].startswith("unavailable")
        if i in DUPLICATES:
            code, why, conf, stage, inc = "DUP", f"duplicate record of paper index {DUPLICATES[i]} (same work)", "high", "title/abstract", "n"
        elif i in RESCREEN:
            code, why, conf = RESCREEN[i]
            stage, inc = "title/abstract re-screen", "" if code == "pending_fulltext" else "n"
        elif i in FT_CANDIDATES:
            code, why, conf, stage, inc = "pending_fulltext", "passes E1-E4 on title/abstract; E5-E6 judged from full text", "n/a", "title/abstract", ""
        elif i in NOFT_IN_SCOPE:
            code, why, conf, stage, inc = "E6", "in scope by abstract (E1-E4) but no openly retrievable full text: " + NOFT_IN_SCOPE[i], "medium", "title/abstract", "n"
        elif i in E1_REVIEW:
            code, why, conf, stage, inc = "E1", "review, perspective, cover or non-primary item", "high", "title/abstract", "n"
        elif i in E3_UV_ONLY:
            code, why, conf, stage, inc = "E3", "UV-only irradiation stated in the abstract", "medium", "title/abstract", "n"
        elif i in E4_NO_PHOTO:
            code, why, conf, stage, inc = "E4", E4_REASONS.get(i, "deconstruction is thermal, chemical, enzymatic or microbial; light not the deconstruction route"), "medium", "title/abstract", "n"
        else:
            code, why = title_code(i, a["title"])
            conf, stage, inc = "medium (title-level category)", "title", "n"
        rows.append({"paper_id": a["paper_id"], "doi": a["doi"], "pmcid": a["pmcid"], "year": a["year"], "title": a["title"],
                     "license": a["license"], "fulltext": a["fulltext"], "include": inc,
                     "exclusion_reason": "" if inc != "n" else code, "reviewer": REVIEWER, "review_date": TODAY})
        log.append({"index": i, "paper_id": a["paper_id"], "code": code, "rationale": why, "confidence": conf, "stage": stage,
                    "has_fulltext": "y" if has_ft else "n"})
    # full-text decisions override
    for f in sorted((ROOT / "data/curated/extractions").glob("*.json")):
        d = json.loads(f.read_text())
        sc = d.get("screen", {})
        for r, l in zip(rows, log):
            if r["pmcid"] == d.get("pmcid"):
                r["include"] = "y" if sc.get("decision") == "include" else "n"
                r["exclusion_reason"] = "" if r["include"] == "y" else sc.get("criteria", "")
                r["reviewer"] = "Claude (AI) full-text screen"
                l.update({"code": "include" if r["include"] == "y" else sc.get("criteria", ""), "rationale": sc.get("rationale", ""),
                          "confidence": sc.get("confidence", ""), "stage": "full text", "evidence_loc": sc.get("evidence_loc", "")})
                l["stage"] = "full text"
                if sc.get("decision") == "ambiguous":
                    l["code"] = "ambiguous"
    with open(ROOT / "data/curated/screening.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    keys = ["index", "paper_id", "code", "rationale", "confidence", "stage", "has_fulltext", "evidence_loc"]
    with open(ROOT / "data/curated/screening_log.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(log)
    import collections
    print(collections.Counter(l["code"] for l in log))


if __name__ == "__main__":
    main()
