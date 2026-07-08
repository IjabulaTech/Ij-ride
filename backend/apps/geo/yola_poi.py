"""Curated Yola / Adamawa places-of-interest.

Why this exists: Mapbox's global index does not know about local Yola
landmarks the way locals do. Typing "AUN" or "FMC" or "Jimeta" gives poor
or empty results. This gazetteer is checked FIRST for every suggest()
call — real Yola places always win the top slots. Mapbox then supplies
the tail for street/address/generic searches.

Adding entries is trivial: append a POI tuple. Aliases are matched
case-insensitively as substrings, so "aun" also matches "AUN" and "American".
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LocalPOI:
    label: str          # Short display name shown in the dropdown
    address: str        # Full address stored on the ride
    lat: Decimal
    lng: Decimal
    place_type: str     # "poi" | "neighborhood" | "landmark" | "hospital" | ...
    aliases: tuple[str, ...] = ()   # Extra strings to match against


YOLA_POIS: tuple[LocalPOI, ...] = (
    # ---- Universities ----
    LocalPOI(
        "American University of Nigeria",
        "American University of Nigeria (AUN), Yola, Adamawa",
        Decimal("9.334500"), Decimal("12.494400"),
        "university", ("AUN", "American University", "American Uni"),
    ),
    LocalPOI(
        "Modibbo Adama University",
        "Modibbo Adama University (MAU), Yola South, Adamawa",
        Decimal("9.202800"), Decimal("12.481000"),
        "university", ("MAU", "MAUTECH", "Modibbo Adama"),
    ),
    LocalPOI(
        "Adamawa State Polytechnic",
        "Adamawa State Polytechnic, Yola, Adamawa",
        Decimal("9.269000"), Decimal("12.451000"),
        "college", ("Poly", "Adamawa Poly", "State Poly"),
    ),
    LocalPOI(
        "Adamawa State University Mubi Campus",
        "Adamawa State University, Mubi, Adamawa",
        Decimal("10.269000"), Decimal("13.259000"),
        "university", ("ADSU", "Adamawa State University"),
    ),

    # ---- Hospitals ----
    LocalPOI(
        "Federal Medical Centre Yola",
        "Federal Medical Centre (FMC), Yola, Adamawa",
        Decimal("9.215100"), Decimal("12.471200"),
        "hospital", ("FMC", "FMC Yola", "Federal Medical"),
    ),
    LocalPOI(
        "Specialist Hospital Yola",
        "Specialist Hospital, Yola, Adamawa",
        Decimal("9.208000"), Decimal("12.492300"),
        "hospital", ("Specialist Hospital",),
    ),
    LocalPOI(
        "State Hospital Jimeta",
        "State Hospital, Jimeta, Yola North, Adamawa",
        Decimal("9.267500"), Decimal("12.453500"),
        "hospital", ("Jimeta Hospital",),
    ),

    # ---- Markets ----
    LocalPOI(
        "Jimeta Main Market",
        "Jimeta Main Market, Jimeta, Yola North, Adamawa",
        Decimal("9.273500"), Decimal("12.464200"),
        "market", ("Jimeta Market", "Main Market", "Jimeta"),
    ),
    LocalPOI(
        "Jimeta Modern Market",
        "Jimeta Modern Market, Yola North, Adamawa",
        Decimal("9.261100"), Decimal("12.447300"),
        "market", ("Modern Market",),
    ),
    LocalPOI(
        "Yola Main Market",
        "Yola Main Market, Yola Town, Adamawa",
        Decimal("9.201500"), Decimal("12.494100"),
        "market", ("Yola Market", "Yola Town Market"),
    ),

    # ---- Transport ----
    LocalPOI(
        "Yola International Airport",
        "Yola International Airport, Jimeta, Adamawa",
        Decimal("9.257500"), Decimal("12.430200"),
        "airport", ("Yola Airport", "Airport", "YOL"),
    ),
    LocalPOI(
        "Jimeta Motor Park",
        "Jimeta Motor Park, Yola North, Adamawa",
        Decimal("9.266500"), Decimal("12.462800"),
        "transit", ("Jimeta Park", "Motor Park Jimeta"),
    ),

    # ---- Government ----
    LocalPOI(
        "Government House Yola",
        "Government House, Yola South, Adamawa",
        Decimal("9.204400"), Decimal("12.495600"),
        "government", ("Government House",),
    ),
    LocalPOI(
        "Adamawa State Secretariat",
        "Adamawa State Secretariat, Yola, Adamawa",
        Decimal("9.207600"), Decimal("12.493300"),
        "government", ("Secretariat", "State Secretariat"),
    ),
    LocalPOI(
        "Police Roundabout",
        "Police Roundabout, Yola, Adamawa",
        Decimal("9.210000"), Decimal("12.482000"),
        "roundabout", ("Police",),
    ),
    LocalPOI(
        "Army Barracks Yola",
        "Army Barracks, Yola, Adamawa",
        Decimal("9.240000"), Decimal("12.450000"),
        "military", ("Army Barracks", "Barracks", "Army"),
    ),

    # ---- Neighborhoods / areas ----
    LocalPOI(
        "Jimeta", "Jimeta, Yola North, Adamawa",
        Decimal("9.267000"), Decimal("12.455000"),
        "locality", (),
    ),
    LocalPOI(
        "Yola Town", "Yola Town, Yola South, Adamawa",
        Decimal("9.200000"), Decimal("12.494000"),
        "locality", ("Yola South Town",),
    ),
    LocalPOI(
        "Karewa GRA",
        "Karewa GRA, Jimeta, Yola North, Adamawa",
        Decimal("9.275500"), Decimal("12.451700"),
        "neighborhood", ("Karewa",),
    ),
    LocalPOI(
        "Bekaji",
        "Bekaji, Jimeta, Yola North, Adamawa",
        Decimal("9.266400"), Decimal("12.456000"),
        "neighborhood", ("Bekaji Roundabout",),
    ),
    LocalPOI(
        "Doubeli",
        "Doubeli, Yola South, Adamawa",
        Decimal("9.227000"), Decimal("12.505800"),
        "neighborhood", ("Doubeli Bypass",),
    ),
    LocalPOI(
        "Damilu",
        "Damilu, Yola North, Adamawa",
        Decimal("9.287000"), Decimal("12.439000"),
        "neighborhood", (),
    ),
    LocalPOI(
        "Nassarawo",
        "Nassarawo, Jimeta, Yola North, Adamawa",
        Decimal("9.265000"), Decimal("12.472000"),
        "neighborhood", ("Nasarawo",),
    ),
    LocalPOI(
        "Wuro Hausa",
        "Wuro Hausa, Yola, Adamawa",
        Decimal("9.250000"), Decimal("12.460000"),
        "neighborhood", (),
    ),
    LocalPOI(
        "Yolde Pate",
        "Yolde Pate, Yola South, Adamawa",
        Decimal("9.228000"), Decimal("12.524000"),
        "neighborhood", (),
    ),
    LocalPOI(
        "Vinikilang",
        "Vinikilang, Girei, Adamawa",
        Decimal("9.320000"), Decimal("12.530000"),
        "neighborhood", (),
    ),
    LocalPOI(
        "Sangere",
        "Sangere, Yola South, Adamawa",
        Decimal("9.312200"), Decimal("12.498800"),
        "neighborhood", ("Sangere Junction",),
    ),
    LocalPOI(
        "Girei",
        "Girei Town, Adamawa",
        Decimal("9.361100"), Decimal("12.552200"),
        "locality", (),
    ),
    LocalPOI(
        "Shagari Low Cost",
        "Shagari Low Cost Housing Estate, Yola, Adamawa",
        Decimal("9.210000"), Decimal("12.460000"),
        "neighborhood", ("Shagari", "Shagari Housing", "Low Cost"),
    ),

    # ---- Roads ----
    LocalPOI(
        "Mubi Road",
        "Mubi Road, Jimeta, Yola, Adamawa",
        Decimal("9.268000"), Decimal("12.467000"),
        "road", ("Mubi Rd",),
    ),
    LocalPOI(
        "Numan Road",
        "Numan Road, Yola, Adamawa",
        Decimal("9.210000"), Decimal("12.455000"),
        "road", ("Numan Rd",),
    ),
    LocalPOI(
        "Bank Road",
        "Bank Road, Jimeta, Yola North, Adamawa",
        Decimal("9.267500"), Decimal("12.459500"),
        "road", (),
    ),
    LocalPOI(
        "Atiku Abubakar Road",
        "Atiku Abubakar Road, Yola, Adamawa",
        Decimal("9.208000"), Decimal("12.490000"),
        "road", ("Atiku Road",),
    ),
)


def match(query: str, limit: int = 5) -> list[LocalPOI]:
    """Return POIs whose label / address / any alias contains the query.
    Case-insensitive substring match; longer matches beat shorter ones."""
    q = query.strip().lower()
    if not q:
        return []
    scored: list[tuple[int, int, LocalPOI]] = []
    for i, poi in enumerate(YOLA_POIS):
        haystacks = (poi.label, poi.address, *poi.aliases)
        best_hit = -1
        for h in haystacks:
            idx = h.lower().find(q)
            if idx != -1 and (best_hit == -1 or idx < best_hit):
                best_hit = idx
        if best_hit != -1:
            # Prefer prefix matches (best_hit == 0) and preserve declared order for ties
            scored.append((best_hit, i, poi))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [poi for _, _, poi in scored[:limit]]
