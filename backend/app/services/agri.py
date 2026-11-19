"""Irrigation-water advisory. Values follow FAO Irrigation & Drainage Paper 29 (Ayers & Westcot)
screening guidance. Advisory only: soil and lab testing and local agronomist input (e.g. TNAU / KVK) are required."""

CROP_GROUPS = [  # approximate ECe threshold (dS/m) groupings; verify locally
    ("Sensitive (≈<1.5 dS/m soil EC)", ["beans", "onion", "carrot", "strawberry"]),
    ("Moderately sensitive (≈1.5–4)", ["maize", "tomato", "groundnut", "rice (seedling stage is sensitive)"]),
    ("Moderately tolerant (≈4–8)", ["cotton", "sorghum", "coconut", "date palm", "sugarcane (reduced yield)"]),
    ("Tolerant (≈>8)", ["barley", "salt-tolerant grasses", "casuarina (windbreak)"]),
]


def irrigation_suitability(ec_us_cm=None, chloride_mg_l=None, sar=None):
    notes, level = [], 0
    if ec_us_cm is not None:
        ds = ec_us_cm / 1000
        if ds < 0.7: lv, msg = 0, "No salinity restriction expected (ECw < 0.7 dS/m)."
        elif ds <= 3.0: lv, msg = 1, "Slight to moderate restriction (ECw 0.7–3.0 dS/m): choose tolerant crops, add leaching fraction."
        else: lv, msg = 2, "Severe restriction (ECw > 3.0 dS/m): only tolerant crops with good drainage."
        level = max(level, lv); notes.append(msg)
    if chloride_mg_l is not None:
        if chloride_mg_l < 142: lv, msg = 0, "Chloride: no leaf-injury concern (<142 mg/L)."
        elif chloride_mg_l <= 355: lv, msg = 1, "Chloride: slight–moderate leaf-burn risk with sprinklers (142–355 mg/L)."
        else: lv, msg = 2, "Chloride: severe toxicity risk for sensitive crops (>355 mg/L)."
        level = max(level, lv); notes.append(msg)
    if sar is not None:
        notes.append(f"SAR = {sar}. Interpret together with EC (infiltration risk); test soil structure.")
    label = ["Suitable", "Use with management", "Severely restricted"][level]
    return {"suitability": label, "notes": notes}


def blending(ec_saline, ec_fresh, target_ec):
    """Fraction of freshwater needed so the mix reaches target_ec (linear EC mixing approximation)."""
    if not ec_fresh < target_ec <= ec_saline:
        return None
    f = (ec_saline - target_ec) / (ec_saline - ec_fresh)
    return {"fresh_fraction": round(f, 2), "saline_fraction": round(1 - f, 2),
            "note": "Linear approximation; verify mixed-water EC and chemistry by testing."}


def advisory(ec=None, chloride=None, sar=None):
    out = irrigation_suitability(ec, chloride, sar)
    tier = {"Suitable": 0, "Use with management": 2, "Severely restricted": 3}[out["suitability"]]
    out["crop_groups"] = [{"group": g, "examples": c} for g, c in CROP_GROUPS[tier:] ] if tier else \
        [{"group": g, "examples": c} for g, c in CROP_GROUPS]
    out["management"] = ["Apply a leaching fraction and maintain drainage.",
                         "Prefer drip over sprinkler for chloride-sensitive crops.",
                         "Monitor soil EC (saturated-paste ECe) each season.",
                         "Blend with fresh/rain-harvested water where available."]
    out["disclaimer"] = "Screening guidance only. Confirm with soil + water lab tests and a local agricultural officer."
    return out
