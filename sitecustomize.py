"""Runtime compatibility patch for route timeline rows."""

from __future__ import annotations

try:
    import pandas as _pd
except Exception:
    _pd = None

if _pd is not None and not getattr(_pd.Series, "_route_mew_key_fallback", False):
    _series_getitem = _pd.Series.__getitem__
    _fallback_keys = {
        "brand": "型態",
        "name": "門市",
        "address": "地址",
    }

    def _route_mew_getitem(self, key):
        if isinstance(key, str) and key not in self.index:
            fallback_key = _fallback_keys.get(key)
            if fallback_key in self.index:
                return _series_getitem(self, fallback_key)
        return _series_getitem(self, key)

    _pd.Series.__getitem__ = _route_mew_getitem
    _pd.Series._route_mew_key_fallback = True
