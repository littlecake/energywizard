"""Validated optional fixed-price and HDO settings; absent fields preserve old clients."""
import math
import re


def extended_price_options(body):
    result = {}
    for field in ("buy_mode", "sell_mode"):
        if field in body:
            if body[field] not in ("spot", "fixed"):
                raise ValueError(f"Invalid {field}")
            result["price_" + field] = body[field]
    for field in ("buy_fixed", "sell_fixed", "distribution_nt", "distribution_vt"):
        if field in body:
            try:
                value = float(str(body[field]).replace(",", "."))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid {field}") from None
            if not math.isfinite(value) or not (-100 <= value <= 1000):
                raise ValueError(f"Invalid {field}")
            if field.startswith("distribution_") and value < 0:
                raise ValueError(f"Invalid {field}")
            result["price_" + field] = value
    if "hdo_entity" in body:
        entity = str(body["hdo_entity"] or "").strip()
        if entity and not re.fullmatch(r"sensor\.[a-z0-9_]+", entity):
            raise ValueError("Invalid HDO schedule entity")
        result["price_hdo_entity"] = entity or None
    return result
