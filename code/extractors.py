"""Pattern detectors that propose candidate values from article text and tables.

Every detector returns dicts with: field, value, unit, raw (the matched span). They never
decide which value belongs to which record; that pairing is the curator's job. Recall is
favoured over precision because every candidate is reviewed by a person.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- normalisation

_MINUS = "−–—‐‑"


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for ch in _MINUS:
        s = s.replace(ch, "-")
    s = s.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", s)


NUM = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"


def to_float(s: str) -> float:
    return float(s.replace(",", ""))


# ---------------------------------------------------------------- molar mass

MASS_UNITS = [
    (r"kg\s*/\s*mol|kg\s*mol\s*-?\s*1|kg\s*mol-1|kg\.mol-1|kg/mol", "kg/mol"),
    (r"g\s*/\s*mol|g\s*mol\s*-?\s*1|g\.mol-1|g/mol", "g/mol"),
    (r"kDa|kD\b", "kDa"),
    (r"(?<![km])Da\b", "Da"),
]
_UNIT_RE = "|".join(f"(?:{u})" for u, _ in MASS_UNITS)

MASS_KIND = [
    (r"M\s*n\b|M_n|number[- ]average molecular (?:weight|mass)|number[- ]average molar mass", "Mn"),
    (r"M\s*w\b|M_w|weight[- ]average molecular (?:weight|mass)|weight[- ]average molar mass", "Mw"),
    (r"M\s*p\b|M_p|peak molecular (?:weight|mass)|peak molar mass", "Mp"),
]
_KIND_RE = "|".join(f"(?:{k})" for k, _ in MASS_KIND)

MASS_RE = re.compile(
    rf"(?P<kind>{_KIND_RE})\s*(?:\([^)]{{0,20}}\))?\s*(?:of|was|were|is|=|:|≈|~|decreased from|from|to)?\s*(?:approximately|ca\.?|about)?\s*"
    rf"{NUM.replace('(', '(?P<v1>', 1)}\s*(?P<u1>{_UNIT_RE})?"
    rf"(?:\s*(?:to|→|->)\s*{NUM.replace('(', '(?P<v2>', 1)}\s*(?P<u2>{_UNIT_RE})?)?",
    re.I,
)
DISP_RE = re.compile(rf"(?:Đ|Ð|PDI|dispersity|polydispersity(?: index)?|M\s*w\s*/\s*M\s*n)\s*(?:\([^)]{{0,10}}\))?\s*(?:of|was|were|=|:|≈|~|changed from|decreased from|increased from|from|narrowed from|broadened from)?\s*{NUM.replace('(', '(?P<v>', 1)}"
                     rf"(?:\s*(?:to|→|->)\s*{NUM.replace('(', '(?P<v2>', 1)})?", re.I)


def _unit(u: str | None) -> str:
    if not u:
        return ""
    for pat, name in MASS_UNITS:
        if re.fullmatch(pat, u.strip(), re.I):
            return name
    return u.strip()


def _kind(k: str) -> str:
    for pat, name in MASS_KIND:
        if re.fullmatch(pat, k.strip(), re.I):
            return name
    return k


def find_molar_mass(text: str):
    out = []
    for m in MASS_RE.finditer(text):
        kind = _kind(m.group("kind"))
        u1, u2 = _unit(m.group("u1")), _unit(m.group("u2"))
        out.append({"field": kind, "value": to_float(m.group("v1")), "unit": u1 or u2, "raw": m.group(0)})
        if m.group("v2"):
            out.append({"field": kind, "value": to_float(m.group("v2")), "unit": u2 or u1, "raw": m.group(0),
                        "note": "second value of a from/to pair"})
    for m in DISP_RE.finditer(text):
        v = to_float(m.group("v"))
        if 1.0 <= v <= 20:
            out.append({"field": "dispersity", "value": v, "unit": "", "raw": m.group(0)})
        if m.group("v2"):
            v2 = to_float(m.group("v2"))
            if 1.0 <= v2 <= 20:
                out.append({"field": "dispersity", "value": v2, "unit": "", "raw": m.group(0),
                            "note": "second value of a from/to pair"})
    return out


# ---------------------------------------------------------------- SEC calibration

CALIBRATION = [
    (r"polystyrene (?:standards?|calibration)|PS (?:standards?|calibration)|relative to (?:linear )?polystyrene|against polystyrene", "conventional_PS"),
    (r"PMMA (?:standards?|calibration)|poly\(methyl methacrylate\) (?:standards?|calibration)|relative to PMMA", "conventional_PMMA"),
    (r"PEG (?:standards?|calibration)|PEO (?:standards?|calibration)|poly\(ethylene (?:glycol|oxide)\) standards?", "conventional_PEG_PEO"),
    (r"universal calibration", "universal_calibration"),
    (r"multi-?angle (?:laser )?light scattering|MALS|MALLS|light[- ]scattering detect", "absolute_MALS"),
    (r"triple[- ]detect|viscometr(?:y|ic) detect", "triple_detection"),
    (r"high[- ]temperature (?:GPC|SEC)|HT-?GPC|HT-?SEC|1,2,4-trichlorobenzene", "high_temperature_SEC"),
    (r"\bMALDI\b", "MALDI_TOF"),
    (r"\bDOSY\b", "DOSY_NMR"),
]
SEC_MENTION = re.compile(r"\b(GPC|SEC|size[- ]exclusion|gel permeation)\b", re.I)


def find_calibration(text: str):
    out = []
    for pat, name in CALIBRATION:
        for m in re.finditer(pat, text, re.I):
            out.append({"field": "sec_calibration", "value": name, "unit": "", "raw": m.group(0)})
    for m in re.finditer(r"(?:eluent|mobile phase|eluting with|eluted (?:with|in))\s*(?:was|:)?\s*([A-Za-z0-9(),\- ]{2,40})", text, re.I):
        out.append({"field": "sec_eluent", "value": m.group(1).strip(" ,."), "unit": "", "raw": m.group(0)})
    for m in re.finditer(r"\b(?:SEC|GPC|HT-?GPC|HT-?SEC)\s+(?:analysis\s+)?in\s+(THF|tetrahydrofuran|chloroform|CHCl3|DMF|DMAc|NMP|TCB|1,2,4-trichlorobenzene|HFIP|toluene|water)\b", text, re.I):
        out.append({"field": "sec_eluent", "value": m.group(1), "unit": "", "raw": m.group(0)})
    return out


# ---------------------------------------------------------------- light

COLOR_BANDS = {"violet": "violet", "purple": "violet", "blue": "blue", "cyan": "cyan", "green": "green",
               "yellow": "yellow", "orange": "orange", "red": "red", "white": "white", "warm white": "white"}
WL_RE = re.compile(rf"(?:λ\s*(?:max|em|=)?\s*[=:]?\s*)?{NUM.replace('(', '(?P<v>', 1)}\s*(?:±\s*\d+\s*)?nm\b", re.I)
WL_RANGE_RE = re.compile(r"(?P<a>\d{3})\s*(?:-|to|–)\s*(?P<b>\d{3})\s*nm\b", re.I)
COLOR_RE = re.compile(r"\b(?P<c>violet|purple|blue|cyan|green|yellow|orange|red|warm white|white)\s*(?:LEDs?|light|lamp|Kessil)", re.I)
SUN_RE = re.compile(r"\b(sunlight|solar simulator|AM\s*1\.5G?|xenon lamp|Xe lamp)\b", re.I)
IRR_RE = re.compile(rf"{NUM.replace('(', '(?P<v>', 1)}\s*(?P<u>mW\s*/?\s*cm\s*-?\s*2|mW cm-2|W\s*/?\s*m\s*-?\s*2|W\s*/?\s*cm\s*-?\s*2|W\b)", re.I)


def find_light(text: str):
    out = []
    for m in WL_RANGE_RE.finditer(text):
        a, b = int(m.group("a")), int(m.group("b"))
        if 300 <= a < b <= 900:
            out.append({"field": "wavelength_range_nm", "value": f"{a}-{b}", "unit": "nm", "raw": m.group(0)})
    for m in WL_RE.finditer(text):
        v = to_float(m.group("v"))
        if 300 <= v <= 900:
            out.append({"field": "wavelength_nm", "value": v, "unit": "nm", "raw": m.group(0),
                        **({"note": "outside 380-780 nm visible window"} if not 380 <= v <= 780 else {})})
    for m in COLOR_RE.finditer(text):
        out.append({"field": "light_color", "value": COLOR_BANDS[m.group("c").lower()], "unit": "", "raw": m.group(0)})
    for m in SUN_RE.finditer(text):
        out.append({"field": "light_source", "value": m.group(1), "unit": "", "raw": m.group(0)})
    for m in IRR_RE.finditer(text):
        out.append({"field": "irradiance_or_power", "value": to_float(m.group("v")),
                    "unit": re.sub(r"\s+", "", m.group("u")), "raw": m.group(0)})
    return out


# ---------------------------------------------------------------- time, temperature, atmosphere

TIME_RE = re.compile(rf"{NUM.replace('(', '(?P<v>', 1)}\s*(?P<u>h\b|hrs?\b|hours?\b|min\b|mins\b|minutes?\b|d\b|days?\b|s\b|seconds?\b)", re.I)
TEMP_RE = re.compile(rf"{NUM.replace('(', '(?P<v>', 1)}\s*°\s*C|\b(room temperature|rt|ambient temperature)\b", re.I)
ATM_RE = re.compile(r"\b(under (?:an? )?(?:air|O2|oxygen|N2|nitrogen|argon|Ar)|(?:air|O2|oxygen) (?:atmosphere|balloon)|aerobic|anaerobic|degassed|inert atmosphere)\b", re.I)


def find_time_temp_atm(text: str):
    out = []
    for m in TIME_RE.finditer(text):
        out.append({"field": "time", "value": to_float(m.group("v")), "unit": m.group("u").lower(), "raw": m.group(0)})
    for m in TEMP_RE.finditer(text):
        if m.group("v"):
            out.append({"field": "temperature", "value": to_float(m.group("v")), "unit": "C", "raw": m.group(0)})
        else:
            out.append({"field": "temperature", "value": "room temperature", "unit": "", "raw": m.group(0)})
    for m in ATM_RE.finditer(text):
        out.append({"field": "atmosphere", "value": m.group(1), "unit": "", "raw": m.group(0)})
    return out


# ---------------------------------------------------------------- dictionaries

POLYMERS = {
    # name pattern: (canonical, class)
    r"polystyrene|\bPS\b(?![- ]standard)": ("polystyrene", "vinyl_styrenic"),
    r"poly\(methyl methacrylate\)|\bPMMA\b": ("poly(methyl methacrylate)", "vinyl_methacrylate"),
    r"poly\((?:n-)?butyl acrylate\)|\bPnBA\b|\bPBA\b": ("poly(butyl acrylate)", "vinyl_acrylate"),
    r"poly\(methyl acrylate\)|\bPMA\b": ("poly(methyl acrylate)", "vinyl_acrylate"),
    r"poly\(vinyl chloride\)|polyvinyl chloride|\bPVC\b": ("poly(vinyl chloride)", "vinyl_halogenated"),
    r"poly\(vinyl alcohol\)|polyvinyl alcohol|\bPVA\b|\bPVOH\b": ("poly(vinyl alcohol)", "vinyl_other"),
    r"poly\(vinyl acetate\)|\bPVAc\b": ("poly(vinyl acetate)", "vinyl_other"),
    r"high[- ]density polyethylene|\bHDPE\b": ("HDPE", "polyolefin"),
    r"low[- ]density polyethylene|\bLDPE\b|\bLLDPE\b": ("LDPE", "polyolefin"),
    r"polyethylene(?! terephthalate| glycol| oxide)|\bPE\b": ("polyethylene", "polyolefin"),
    r"polypropylene|\bPP\b": ("polypropylene", "polyolefin"),
    r"poly\(ethylene terephthalate\)|polyethylene terephthalate|\bPET\b": ("poly(ethylene terephthalate)", "polyester"),
    r"poly\(lactic acid\)|polylactide|\bPLA\b|\bPLLA\b": ("poly(lactic acid)", "polyester"),
    r"polycaprolactone|\bPCL\b": ("polycaprolactone", "polyester"),
    r"polycarbonate|\bBPA-PC\b": ("polycarbonate", "polycarbonate"),
    r"polyurethane|\bPU\b": ("polyurethane", "polyurethane"),
    r"nylon|polyamide|\bPA6\b|\bPA66\b": ("polyamide", "polyamide"),
    r"poly\(ethylene glycol\)|poly\(ethylene oxide\)|\bPEG\b|\bPEO\b": ("PEG/PEO", "polyether"),
    r"poly\(phenylene oxide\)|\bPPO\b": ("poly(phenylene oxide)", "polyether"),
    r"lignin": ("lignin", "biopolymer"),
    r"cellulose": ("cellulose", "biopolymer"),
}

CATALYSTS = {
    r"eosin\s*Y": "eosin Y", r"4CzIPN": "4CzIPN", r"Ir\(ppy\)\s*3|fac-Ir\(ppy\)3": "Ir(ppy)3",
    r"\[?Ir\(dF\(CF3\)ppy\)2\(dtbbpy\)\]?\s*PF6": "[Ir(dF(CF3)ppy)2(dtbbpy)]PF6",
    r"\[?Ru\(bpy\)3\]?\s*(?:Cl2|\(PF6\)2|2\+)?": "Ru(bpy)3", r"Mes-?Acr|mesityl acridinium|acridinium": "acridinium",
    r"\bTBADT\b|decatungstate": "decatungstate", r"\bFeCl3\b|iron\(III\) chloride": "FeCl3",
    r"\bCeCl3\b|cerium\(III\) chloride|\bCeCl6\b": "CeCl3/cerium chloride", r"\bCuCl2\b": "CuCl2",
    r"\bTiO2\b|titanium dioxide": "TiO2", r"g-C3N4|graphitic carbon nitride": "g-C3N4",
    r"\bCdS\b": "CdS", r"\bZnO\b": "ZnO", r"\bBiVO4\b": "BiVO4", r"\bWO3\b": "WO3",
    r"riboflavin": "riboflavin", r"thioxanthone": "thioxanthone", r"\bDDQ\b": "DDQ",
    r"anthraquinone": "anthraquinone", r"benzophenone": "benzophenone",
    r"\bHAT\b catalyst|hydrogen atom transfer catalyst": "HAT catalyst (unspecified)",
    r"\bNHPI\b|N-hydroxyphthalimide": "NHPI", r"\bHCl\b": "HCl", r"\bTfOH\b|triflic acid": "TfOH",
    r"porphyrin": "porphyrin", r"phenothiazine": "phenothiazine", r"\bPDI\b catalyst|perylene": "perylene diimide",
}
CATALYST_CUE = re.compile(r"\b(photocatalysts?|photoredox catalysts?|photosensiti[sz]ers?|catalysts?)\b", re.I)

SOLVENTS = {
    r"acetonitrile|\bMeCN\b|\bCH3CN\b": "acetonitrile", r"dichloromethane|\bDCM\b|\bCH2Cl2\b": "dichloromethane",
    r"chloroform|\bCHCl3\b": "chloroform", r"\bDMSO\b|dimethyl sulfoxide": "DMSO",
    r"\bDMF\b|dimethylformamide": "DMF", r"tetrahydrofuran|\bTHF\b": "THF", r"\bwater\b|\bH2O\b": "water",
    r"acetone": "acetone", r"benzene(?!s)": "benzene", r"toluene": "toluene",
    r"1,2-dichloroethane|\bDCE\b": "1,2-dichloroethane", r"ethyl acetate|\bEtOAc\b": "ethyl acetate",
    r"methanol|\bMeOH\b": "methanol", r"ethanol|\bEtOH\b": "ethanol", r"hexafluoroisopropanol|\bHFIP\b": "HFIP",
    r"trifluorotoluene|\bPhCF3\b": "trifluorotoluene", r"o-dichlorobenzene|\bODCB\b": "o-dichlorobenzene",
    r"1,2,4-trichlorobenzene|\bTCB\b": "1,2,4-trichlorobenzene", r"solvent[- ]free|neat|solid[- ]state": "solvent-free",
}

PRODUCTS = {
    r"benzoic acid": "benzoic acid", r"benzaldehyde": "benzaldehyde", r"acetophenone": "acetophenone",
    r"formic acid": "formic acid", r"acetic acid": "acetic acid", r"succinic acid": "succinic acid",
    r"terephthalic acid|\bTPA\b": "terephthalic acid", r"methyl methacrylate|\bMMA\b(?! standards)": "methyl methacrylate",
    r"(?<!poly)(?<!poly\()(?<!poly-)styrene\b(?! standards)": "styrene", r"\bCO2\b|carbon dioxide": "CO2", r"\bCO\b|carbon monoxide": "CO",
    r"\bH2\b|hydrogen gas": "H2", r"dibenzoylmethane": "dibenzoylmethane", r"oligomers?": "oligomers",
    r"lactic acid": "lactic acid", r"ethylene glycol": "ethylene glycol", r"monomer": "monomer (unspecified)",
    r"diacids?|dicarboxylic acids?": "dicarboxylic acids",
}
YIELD_RE = re.compile(rf"(?:yield|selectivity|recovered|conversion)\s*(?:of|was|:)?\s*{NUM.replace('(', '(?P<v>', 1)}\s*(?P<u>%|mol%|wt%|wt ?%|mol ?%)", re.I)
LOADING_RE = re.compile(rf"{NUM.replace('(', '(?P<v>', 1)}\s*(?P<u>mol ?%|wt ?%|equiv\.?|eq\.|mg|mmol|µmol|umol|mg ?mL-1|mg/mL|(?-i:mM|M)\b)(?!\s*(?:yield|selectivity|conversion))", re.I)
YIELD_RE2 = re.compile(rf"{NUM.replace('(', '(?P<v>', 1)}\s*(?P<u>%|mol ?%|wt ?%)\s*(?:yield|selectivity|conversion)", re.I)


def _split_top(pat: str):
    parts, depth, cur, esc = [], 0, "", False
    for ch in pat:
        if esc:
            cur += ch
            esc = False
            continue
        if ch == "\\":
            cur += ch
            esc = True
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "|" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


_COMPILED: dict[str, re.Pattern] = {}


def _compile_dict_pattern(pat: str) -> re.Pattern:
    """Full names match case-insensitively; abbreviations written as \\bABC\\b stay case-sensitive
    so 'PS' does not match 'ps' and 'PE' does not match 'pe'."""
    if pat not in _COMPILED:
        alts = []
        for alt in _split_top(pat):
            if re.match(r"^\\b[A-Z0-9]", alt) or re.match(r"^[A-Z][A-Za-z]*\d", alt):
                alts.append(f"(?-i:{alt})")
            else:
                alts.append(alt)
        _COMPILED[pat] = re.compile("|".join(alts), re.I)
    return _COMPILED[pat]


def _dict_hits(text, table, field):
    out = []
    for pat, canon in table.items():
        for m in _compile_dict_pattern(pat).finditer(text):
            val = canon if isinstance(canon, str) else canon[0]
            item = {"field": field, "value": val, "unit": "", "raw": m.group(0)}
            if not isinstance(canon, str):
                item["polymer_class"] = canon[1]
            out.append(item)
    return out


def find_entities(text: str):
    out = []
    out += _dict_hits(text, POLYMERS, "polymer")
    out += _dict_hits(text, CATALYSTS, "catalyst")
    if CATALYST_CUE.search(text):
        out.append({"field": "catalyst_cue", "value": "catalyst mentioned", "unit": "", "raw": CATALYST_CUE.search(text).group(0)})
    out += _dict_hits(text, SOLVENTS, "solvent")
    out += _dict_hits(text, PRODUCTS, "product")
    for m in LOADING_RE.finditer(text):
        out.append({"field": "loading_or_amount", "value": to_float(m.group("v")), "unit": m.group("u").replace(" ", ""), "raw": m.group(0)})
    for rx in (YIELD_RE, YIELD_RE2):
        for m in rx.finditer(text):
            v = to_float(m.group("v"))
            if 0 <= v <= 100:
                out.append({"field": "yield_or_conversion", "value": v, "unit": m.group("u").replace(" ", ""), "raw": m.group(0)})
    return out


def extract_all(text: str):
    t = norm_text(text)
    out = []
    for fn in (find_molar_mass, find_calibration, find_light, find_time_temp_atm, find_entities):
        out += fn(t)
    return out


# ---------------------------------------------------------------- tables

HEADER_KIND = re.compile(rf"^\s*(?P<kind>{_KIND_RE}|Đ|Ð|PDI|dispersity|Mw/Mn)\b(?P<rest>.*)$", re.I)


def table_header_fields(header_cells):
    """Map column index -> (field, unit) for SEC-style headers like 'Mn (kg mol-1)'."""
    cols = {}
    for i, h in enumerate(header_cells):
        h = norm_text(h)
        m = HEADER_KIND.match(h)
        if not m:
            continue
        kind = m.group("kind")
        if re.fullmatch(r"Đ|Ð|PDI|dispersity|Mw/Mn", kind, re.I):
            cols[i] = ("dispersity", "")
            continue
        um = re.search(_UNIT_RE, m.group("rest"), re.I)
        unit = _unit(um.group(0)) if um else ""
        # headers like 'Mn × 10^-3' signal scaling; flag rather than guess
        scale = re.search(r"[x×]\s*10\s*\^?\s*(-?\d+)", m.group("rest"))
        cols[i] = (_kind(kind), unit + (f" [header scale x10^{scale.group(1)}]" if scale else ""))
    for i, h in enumerate(header_cells):
        hl = norm_text(h).lower()
        if i in cols:
            continue
        if re.search(r"\bnm\b|wavelength|λ", hl):
            cols[i] = ("wavelength_nm", "nm")
        elif re.search(r"\btime\b|\bt\s*\(", hl):
            unit = re.search(r"\((h|min|d|s)\)", hl)
            cols[i] = ("time", unit.group(1) if unit else "")
        elif re.search(r"catalyst|\bpc\b", hl):
            cols[i] = ("catalyst", "")
        elif re.search(r"solvent", hl):
            cols[i] = ("solvent", "")
        elif re.search(r"yield|conversion|selectivity", hl):
            cols[i] = ("yield_or_conversion", "%" if "%" in hl else "")
        elif re.search(r"polymer|substrate|entry", hl):
            cols[i] = ("row_label", "")
    return cols


def extract_table(header_cells, rows):
    """Yield candidates from a parsed table. Each candidate carries (row, col)."""
    cols = table_header_fields(header_cells)
    out = []
    for r_i, row in enumerate(rows):
        label = " | ".join(norm_text(c) for c in row[:2])
        for c_i, cell in enumerate(row):
            cell_t = norm_text(cell)
            if c_i in cols:
                field, unit = cols[c_i]
                if field in ("catalyst", "solvent", "row_label"):
                    if cell_t:
                        out.append({"field": field, "value": cell_t, "unit": "", "raw": cell_t, "row": r_i, "col": c_i, "row_label": label})
                    continue
                nums = re.findall(NUM, cell_t)
                if nums:
                    for n in nums[:2]:
                        out.append({"field": field, "value": to_float(n), "unit": unit, "raw": cell_t, "row": r_i, "col": c_i, "row_label": label,
                                    **({"note": "cell holds two numbers"} if len(nums) > 1 else {})})
            # free-text cells still go through the entity detectors
            for cand in find_entities(cell_t) + find_light(cell_t):
                cand.update({"row": r_i, "col": c_i, "row_label": label})
                out.append(cand)
    return out, cols
