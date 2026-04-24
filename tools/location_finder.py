import difflib
import unicodedata
import re

KERALA_COASTAL_LOCATIONS = [
    "Kumbla", "Koipadi", "Mogral", "Adakathbail",
    "Kasaragod", "ThalangarJetty", "Kotikulam",
    "Bekal", "Pallikere", "Chittari",
    "Ajanoor-N-Bella", "Hosdrug", "Nileswaram",
    "Thaikadappuram", "BadagaraAzhithala",
    "CheruvathurFH", "Maniyat", "Kavvayi",
    "Kunnariyam", "Ettikulam", "Azhikal",
    "Valapattanam", "Azheecode", "AzheecodeSouth",
    "Kannur", "AyikkaraFH", "Edakkad",
    "Muzhuppilangad", "Tellicherry", "NewMahe",
    "ChombalaFH", "Uralungal", "Nalliyankara",
    "Badagara", "Puduppanam", "Kottakkal",
    "Kizhur", "Tikkoti", "Moodady",
    "Thikkodi(Kodikkal)", "Kadalur Pt",
    "Quilandy/Koloth(Defunct)", "Kollam",
    "Poilkavu", "Chemancheri", "Kappad",
    "Elathur", "PuthiyappaFH", "Puthengadi/Paravanna",
    "Kunduparabu", "Parapanangadi", "Nadakkavu",
    "Kadalundinagaram", "Vellayil", "Beypore",
    "Calicut", "Chaliyam", "VadakkeKadappuram",
    "BeyporeFH", "Ramanattukara", "Thanur",
    "Paravannangadi", "Purattur", "Ponnani",
    "Vakkad", "Koottayi", "Veliyangod",
    "Palappetty", "Attupuram", "Mannalamkunnu",
    "Vayilattur", "Panchavadi", "Edakazhiyur",
    "Blangad", "Chavakkad", "Mullassheri",
    "Vadanappally", "Thalikulam", "Nattika",
    "Kazhimbram", "Edamuttam", "Palapetty",
    "KaipamangalamVanchipura",
    "PerinjanamAraattukadavu", "Kulimuttam",
    "Kara", "Eriyad(Chelarappa)", "Pullut",
    "Kodungallur", "MunambamFH", "Manakodam",
    "Kuzhuppilly", "Cherai", "Edavanakad",
    "Vadakkal", "Puthenkadappuram", "Narakkal",
    "Nayarambalam", "Malipuram", "Ernakulam",
    "Murikumpadam", "Kalamukku",
    "Arthunkal/Chennavely", "Aratungal", "Chethy",
    "Kottamkulangara", "Pollethai", "Thumpolly",
    "Punnappra", "Valanjavazhy", "Thazhampally",
    "Ambalapuzha", "Kalarkod", "AlleppeyBeach",
    "Purakkad", "Thottappally", "Thrikunnapuzha",
    "Padiyamkara Tekku", "Ramancheri Tura",
    "AzheekalJetty", "Alappattu", "Cheriazheekal",
    "Kovilthottam", "Chavara", "Puthenthura",
    "Vettuthura", "Neendakara", "Sakthikulangara",
    "Thankassery F.H.", "QuilonPort", "Quilon",
    "Wadi", "Moothakara", "Pallithottam",
    "Eravipuram", "Tanni", "Pozhikkara",
    "Paravoor", "Edava", "Kappil", "Edaval",
    "Vettoor", "Chilakkoor",
    "Arivalam&Rathikkal", "Mampally",
    "AnjengoNorth", "AnjengoSouth", "Poothura",
    "Perumathura", "Puthukurichi", "Puthenthoppu",
    "St.Andrews", "Pallithura", "Thumba",
    "Valiaveli", "Kochuveli", "Vell",
    "Vettucaud", "Kannanthura", "Kochuthoppu",
    "Trivandrum", "Valiathura/ValiathuraPier",
    "Cheriathura", "Bheemapally", "Poonthura",
    "Tiruvallam", "PanathuraSouth", "Kovalad",
    "Mariyanadu", "Adimalathura",
    "Vizhinjam&Kottapuram", "VizhinjamNorth",
    "Vilinjam",
]

LOCATION_TO_DISTRICT = {
    "Kumbla": "Kasaragod",
    "Koipadi": "Kasaragod",
    "Mogral": "Kasaragod",
    "Adakathbail": "Kasaragod",
    "Kasaragod": "Kasaragod",
    "ThalangarJetty": "Kasaragod",
    "Kotikulam": "Kasaragod",
    "Bekal": "Kasaragod",
    "Pallikere": "Kasaragod",
    "Chittari": "Kasaragod",
    "Ajanoor-N-Bella": "Kasaragod",
    "Hosdrug": "Kasaragod",
    "Nileswaram": "Kasaragod",
    "Thaikadappuram": "Kasaragod",
    "BadagaraAzhithala": "Kannur",
    "CheruvathurFH": "Kannur",
    "Maniyat": "Kannur",
    "Kavvayi": "Kannur",
    "Kunnariyam": "Kannur",
    "Ettikulam": "Kannur",
    "Azhikal": "Kannur",
    "Valapattanam": "Kannur",
    "Azheecode": "Kannur",
    "AzheecodeSouth": "Kannur",
    "Kannur": "Kannur",
    "AyikkaraFH": "Kannur",
    "Edakkad": "Kannur",
    "Muzhuppilangad": "Kannur",
    "Tellicherry": "Kannur",
    "NewMahe": "Kannur",
    "ChombalaFH": "Kozhikode",
    "Uralungal": "Kozhikode",
    "Nalliyankara": "Kozhikode",
    "Badagara": "Kozhikode",
    "Puduppanam": "Kozhikode",
    "Kottakkal": "Kozhikode",
    "Kizhur": "Kozhikode",
    "Tikkoti": "Kozhikode",
    "Moodady": "Kozhikode",
    "Thikkodi(Kodikkal)": "Kozhikode",
    "Kadalur Pt": "Kozhikode",
    "Quilandy/Koloth(Defunct)": "Kozhikode",
    "Kollam": "Kozhikode",
    "Poilkavu": "Kozhikode",
    "Chemancheri": "Kozhikode",
    "Kappad": "Kozhikode",
    "Elathur": "Kozhikode",
    "PuthiyappaFH": "Kozhikode",
    "Puthengadi/Paravanna": "Kozhikode",
    "Kunduparabu": "Kozhikode",
    "Parapanangadi": "Malappuram",
    "Nadakkavu": "Kozhikode",
    "Kadalundinagaram": "Kozhikode",
    "Vellayil": "Kozhikode",
    "Beypore": "Kozhikode",
    "Calicut": "Kozhikode",
    "Chaliyam": "Kozhikode",
    "VadakkeKadappuram": "Kozhikode",
    "BeyporeFH": "Kozhikode",
    "Ramanattukara": "Kozhikode",
    "Thanur": "Malappuram",
    "Paravannangadi": "Malappuram",
    "Purattur": "Malappuram",
    "Ponnani": "Malappuram",
    "Vakkad": "Malappuram",
    "Koottayi": "Malappuram",
    "Veliyangod": "Malappuram",
    "Palappetty": "Thrissur",
    "Attupuram": "Thrissur",
    "Mannalamkunnu": "Thrissur",
    "Vayilattur": "Thrissur",
    "Panchavadi": "Thrissur",
    "Edakazhiyur": "Thrissur",
    "Blangad": "Thrissur",
    "Chavakkad": "Thrissur",
    "Mullassheri": "Thrissur",
    "Vadanappally": "Thrissur",
    "Thalikulam": "Thrissur",
    "Nattika": "Thrissur",
    "Kazhimbram": "Thrissur",
    "Edamuttam": "Thrissur",
    "Palapetty": "Thrissur",
    "KaipamangalamVanchipura": "Thrissur",
    "PerinjanamAraattukadavu": "Thrissur",
    "Kulimuttam": "Thrissur",
    "Kara": "Thrissur",
    "Eriyad(Chelarappa)": "Thrissur",
    "Pullut": "Thrissur",
    "Kodungallur": "Thrissur",
    "MunambamFH": "Ernakulam",
    "Manakodam": "Ernakulam",
    "Kuzhuppilly": "Ernakulam",
    "Cherai": "Ernakulam",
    "Edavanakad": "Ernakulam",
    "Vadakkal": "Ernakulam",
    "Puthenkadappuram": "Ernakulam",
    "Narakkal": "Ernakulam",
    "Nayarambalam": "Ernakulam",
    "Malipuram": "Ernakulam",
    "Ernakulam": "Ernakulam",
    "Murikumpadam": "Ernakulam",
    "Kalamukku": "Ernakulam",
    "Arthunkal/Chennavely": "Alappuzha",
    "Aratungal": "Alappuzha",
    "Chethy": "Alappuzha",
    "Kottamkulangara": "Alappuzha",
    "Pollethai": "Alappuzha",
    "Thumpolly": "Alappuzha",
    "Punnappra": "Alappuzha",
    "Valanjavazhy": "Alappuzha",
    "Thazhampally": "Alappuzha",
    "Ambalapuzha": "Alappuzha",
    "Kalarkod": "Alappuzha",
    "AlleppeyBeach": "Alappuzha",
    "Purakkad": "Alappuzha",
    "Thottappally": "Alappuzha",
    "Thrikunnapuzha": "Alappuzha",
    "Padiyamkara Tekku": "Alappuzha",
    "Ramancheri Tura": "Alappuzha",
    "AzheekalJetty": "Alappuzha",
    "Alappattu": "Alappuzha",
    "Cheriazheekal": "Alappuzha",
    "Kovilthottam": "Kollam",
    "Chavara": "Kollam",
    "Puthenthura": "Kollam",
    "Vettuthura": "Kollam",
    "Neendakara": "Kollam",
    "Sakthikulangara": "Kollam",
    "Thankassery F.H.": "Kollam",
    "QuilonPort": "Kollam",
    "Quilon": "Kollam",
    "Wadi": "Kollam",
    "Moothakara": "Kollam",
    "Pallithottam": "Kollam",
    "Eravipuram": "Kollam",
    "Tanni": "Kollam",
    "Pozhikkara": "Kollam",
    "Paravoor": "Kollam",
    "Edava": "Thiruvananthapuram",
    "Kappil": "Thiruvananthapuram",
    "Edaval": "Thiruvananthapuram",
    "Vettoor": "Thiruvananthapuram",
    "Chilakkoor": "Thiruvananthapuram",
    "Arivalam&Rathikkal": "Thiruvananthapuram",
    "Mampally": "Thiruvananthapuram",
    "AnjengoNorth": "Thiruvananthapuram",
    "AnjengoSouth": "Thiruvananthapuram",
    "Poothura": "Thiruvananthapuram",
    "Perumathura": "Thiruvananthapuram",
    "Puthukurichi": "Thiruvananthapuram",
    "Puthenthoppu": "Thiruvananthapuram",
    "St.Andrews": "Thiruvananthapuram",
    "Pallithura": "Thiruvananthapuram",
    "Thumba": "Thiruvananthapuram",
    "Valiaveli": "Thiruvananthapuram",
    "Kochuveli": "Thiruvananthapuram",
    "Vell": "Thiruvananthapuram",
    "Vettucaud": "Thiruvananthapuram",
    "Kannanthura": "Thiruvananthapuram",
    "Kochuthoppu": "Thiruvananthapuram",
    "Trivandrum": "Thiruvananthapuram",
    "Valiathura/ValiathuraPier": "Thiruvananthapuram",
    "Cheriathura": "Thiruvananthapuram",
    "Bheemapally": "Thiruvananthapuram",
    "Poonthura": "Thiruvananthapuram",
    "Tiruvallam": "Thiruvananthapuram",
    "PanathuraSouth": "Thiruvananthapuram",
    "Kovalad": "Thiruvananthapuram",
    "Mariyanadu": "Thiruvananthapuram",
    "Adimalathura": "Thiruvananthapuram",
    "Vizhinjam&Kottapuram": "Thiruvananthapuram",
    "VizhinjamNorth": "Thiruvananthapuram",
    "Vilinjam": "Thiruvananthapuram",
}


def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


# Common abbreviations / alternate names → canonical location names
_ALIASES: dict[str, list[str]] = {
    "thalassery": ["Tellicherry"],
    "vizhinjam": ["Vizhinjam&Kottapuram", "VizhinjamNorth", "Vilinjam"],
    "munambam": ["MunambamFH"],
}

# District aliases — matching these expands to ALL locations in that district
_DISTRICT_ALIASES: dict[str, str] = {
    "kochi":              "Ernakulam",
    "cochin":             "Ernakulam",
    "ekm":                "Ernakulam",
    "ernakulam":          "Ernakulam",
    "kozhikode":          "Kozhikode",
    "calicut":            "Kozhikode",
    "clt":                "Kozhikode",
    "tvm":                "Thiruvananthapuram",
    "trivandrum":         "Thiruvananthapuram",
    "thiruvananthapuram": "Thiruvananthapuram",
    "alappuzha":          "Alappuzha",
    "alleppey":           "Alappuzha",
    "kollam":             "Kollam",
    "quilon":             "Kollam",
    "thrissur":           "Thrissur",
    "malappuram":         "Malappuram",
    "kannur":             "Kannur",
    "kasaragod":          "Kasaragod",
}


def find_location(query: str, max_results: int = 20) -> list:
    """Relevance-ranked search against KERALA_COASTAL_LOCATIONS.

    Scoring tiers (higher = better):
      100  — exact match (case-insensitive)
       80  — query matches the start of a location name (prefix)
       60  — query matches the start of any word in the name
       40  — query is a substring anywhere in the name
       20  — fuzzy match via difflib (scaled by similarity ratio)
       70  — alias / abbreviation match

    Returns up to *max_results* strings as "Name (District)".
    """
    q_norm = _normalize(query)
    if not q_norm:
        return []

    scored: dict[str, float] = {}

    for loc in KERALA_COASTAL_LOCATIONS:
        loc_norm = _normalize(loc)

        # Exact
        if loc_norm == q_norm:
            scored[loc] = 100
            continue

        # Prefix
        if loc_norm.startswith(q_norm):
            # Boost shorter names (closer to an exact match)
            length_bonus = min(len(q_norm) / max(len(loc_norm), 1), 1.0) * 10
            scored[loc] = 80 + length_bonus
            continue

        # Word-start: split on non-alpha boundaries and check each token
        tokens = re.split(r"[^a-z0-9]+", loc_norm)
        if any(t.startswith(q_norm) for t in tokens if t):
            scored[loc] = 60
            continue

        # Substring anywhere
        if q_norm in loc_norm:
            scored[loc] = 40
            continue

    # Specific alias lookup (e.g. "thalassery" → Tellicherry)
    for alias, targets in _ALIASES.items():
        if alias.startswith(q_norm) or q_norm in alias:
            for loc in targets:
                if loc not in scored or scored[loc] < 70:
                    scored[loc] = 70

    # District alias lookup — expand to ALL locations in the matched district
    for alias, district in _DISTRICT_ALIASES.items():
        if alias.startswith(q_norm) or q_norm == alias:
            for loc, loc_district in LOCATION_TO_DISTRICT.items():
                if loc_district == district:
                    if loc not in scored or scored[loc] < 65:
                        scored[loc] = 65

    # Fuzzy matching — lower cutoff for short queries so single-char still works
    cutoff = 0.3 if len(q_norm) <= 3 else 0.45
    lower_map = {_normalize(loc): loc for loc in KERALA_COASTAL_LOCATIONS}
    fuzzy_hits = difflib.get_close_matches(
        q_norm, list(lower_map.keys()), n=max_results, cutoff=cutoff
    )
    for i, hit in enumerate(fuzzy_hits):
        loc = lower_map[hit]
        ratio = difflib.SequenceMatcher(None, q_norm, hit).ratio()
        fuzzy_score = 20 * ratio   # 0-20 range
        if loc not in scored or scored[loc] < fuzzy_score:
            scored[loc] = fuzzy_score

    # Sort by score descending, then alphabetically for ties
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))

    results = []
    for loc, _score in ranked[:max_results]:
        district = LOCATION_TO_DISTRICT.get(loc, "Unknown")
        results.append(f"{loc}, {district}")
    return results


def get_locations_by_district(district: str) -> list:
    """Return all coastal locations belonging to a district."""
    d_lower = district.lower()
    return [
        loc for loc, dist in LOCATION_TO_DISTRICT.items()
        if dist.lower() == d_lower
    ]


def get_district_for_location(location: str) -> str | None:
    """Return district for an exact location name, or None."""
    return LOCATION_TO_DISTRICT.get(location)
