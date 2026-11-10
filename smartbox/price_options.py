"""Validated optional fixed-price and HDO settings; absent fields preserve old clients."""
import math
import re


def extended_price_options(body):
    result = {}
    for field in ("buy_mode", "sell_mode"):
        if field in body:
            if body[field] not in ("spot", "fixed"):
                raise ValueError(f"Ogiltigt värde: {field}")
            result["price_" + field] = body[field]
    for field in ("buy_fixed", "sell_fixed", "distribution_nt", "distribution_vt"):
        if field in body:
            if body[field] in (None, ""):
                result["price_" + field] = None
                continue
            try:
                value = float(str(body[field]).replace(",", "."))
            except (ValueError, TypeError):
                raise ValueError(f"Ogiltigt värde: {field}") from None
            if not math.isfinite(value) or not (-100 <= value <= 1000):
                raise ValueError(f"Ogiltigt värde: {field}")
            if field.startswith("distribution_") and value < 0:
                raise ValueError(f"Ogiltigt värde: {field}")
            result["price_" + field] = value
    if "hdo_entity" in body:
        entity = str(body["hdo_entity"] or "").strip()
        if entity and not re.fullmatch(r"sensor\.[a-z0-9_]+", entity):
            raise ValueError("Ogiltig entitet för HDO-schema")
        result["price_hdo_entity"] = entity or None
    for side in ("buy", "sell"):
        if body.get(side + "_mode") == "fixed" and result.get("price_" + side + "_fixed") is None:
            raise ValueError("Ange ett fast pris när fast avtal är valt")
    if result.get("price_hdo_entity") and any(result.get("price_distribution_" + tariff) is None for tariff in ("nt", "vt")):
        raise ValueError("Ange båda distributionsavgifterna när HDO används")
    return result
