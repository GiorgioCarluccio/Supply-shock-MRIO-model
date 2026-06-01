"""Parse and classify SAM account labels.

Every SAM account has a canonical label of the form::

    region_code__sector_code__macrosector_code

using a double underscore (``__``) as separator, for example::

    ITC11__A01__A        (productive: agriculture)
    ITC11__C10-12__I     (productive: industry)
    ITC11__M69_70__S     (productive: services)
    EU-ITA__LAB__L       (value added: labour)
    EU-ITA__CAP__K       (value added: capital)
    EU-ITA__TAX__T       (value added: indirect taxes)
    EU-ITA__HH__HH       (final demand: households)
    EU-ITA__CF__CF       (final demand: capital formation)
    EU-ITA__GOV__G       (final demand: government)
    EU-ITA__ROW__R       (final demand: rest of world)

The macrosector code (the third part of the label) is the primary
classification key for the modelling layer.
"""

from __future__ import annotations

LABEL_SEPARATOR = "__"

# Macrosector codes that define each account class.
PRODUCTIVE_MACROSECTORS = frozenset({"A", "I", "S"})
FINAL_DEMAND_MACROSECTORS = frozenset({"HH", "CF", "G", "R"})
VALUE_ADDED_MACROSECTORS = frozenset({"L", "K", "T"})

# Classification result constants.
PRODUCTIVE = "productive"
FINAL_DEMAND = "final_demand"
VALUE_ADDED = "value_added"
OTHER_INSTITUTIONAL = "other_institutional"
UNKNOWN = "unknown"


def parse_account_label(label: str) -> dict:
    """Split a canonical account label into its three component codes.

    Parameters
    ----------
    label:
        Account label of the form ``region__sector__macrosector``.

    Returns
    -------
    dict
        ``{"region_code": ..., "sector_code": ..., "macrosector_code": ...}``.

    Raises
    ------
    ValueError
        If ``label`` is not a string or does not split into exactly three
        non-empty parts on the ``__`` separator.
    """
    if not isinstance(label, str):
        raise ValueError(f"Account label must be a string, got {type(label)!r}.")

    parts = label.split(LABEL_SEPARATOR)
    if len(parts) != 3:
        raise ValueError(
            f"Malformed account label {label!r}: expected exactly three parts "
            f"separated by {LABEL_SEPARATOR!r} (region__sector__macrosector), "
            f"got {len(parts)} part(s)."
        )
    if any(part == "" for part in parts):
        raise ValueError(
            f"Malformed account label {label!r}: one or more parts are empty."
        )

    region_code, sector_code, macrosector_code = parts
    return {
        "region_code": region_code,
        "sector_code": sector_code,
        "macrosector_code": macrosector_code,
    }


def classify_account(parsed_label: dict) -> str:
    """Classify a parsed account label by its macrosector code.

    Parameters
    ----------
    parsed_label:
        Mapping that contains at least a ``macrosector_code`` key, as returned
        by :func:`parse_account_label`.

    Returns
    -------
    str
        One of ``"productive"``, ``"final_demand"``, ``"value_added"``,
        ``"other_institutional"`` or ``"unknown"``.

    Raises
    ------
    ValueError
        If ``parsed_label`` does not contain a ``macrosector_code`` key.
    """
    if "macrosector_code" not in parsed_label:
        raise ValueError(
            "parsed_label must contain a 'macrosector_code' key; "
            "pass the output of parse_account_label()."
        )

    macrosector = parsed_label["macrosector_code"]
    if macrosector in PRODUCTIVE_MACROSECTORS:
        return PRODUCTIVE
    if macrosector in FINAL_DEMAND_MACROSECTORS:
        return FINAL_DEMAND
    if macrosector in VALUE_ADDED_MACROSECTORS:
        return VALUE_ADDED
    # Macrosector codes that are neither productive, final demand nor value
    # added are treated as other institutional accounts when they are clearly
    # non-empty institutional codes; everything else is unknown.
    if isinstance(macrosector, str) and macrosector.strip():
        return OTHER_INSTITUTIONAL
    return UNKNOWN


def build_label(region_code: str, sector_code: str, macrosector_code: str) -> str:
    """Build a canonical ``region__sector__macrosector`` label."""
    return LABEL_SEPARATOR.join([region_code, sector_code, macrosector_code])
