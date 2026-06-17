"""Proxy to real pandas with route-row key compatibility."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_shim_name = __name__
_shim_dir = str(Path(__file__).resolve().parent)
_original_sys_path = list(sys.path)

try:
    sys.modules.pop(_shim_name, None)
    sys.path = [
        path
        for path in sys.path
        if path and str(Path(path).resolve()) != _shim_dir
    ]
    _real_pandas = importlib.import_module(_shim_name)
finally:
    sys.path = _original_sys_path

if not getattr(_real_pandas.Series, "_route_mew_key_fallback", False):
    _series_getitem = _real_pandas.Series.__getitem__
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

    _real_pandas.Series.__getitem__ = _route_mew_getitem
    _real_pandas.Series._route_mew_key_fallback = True

sys.modules[_shim_name] = _real_pandas
globals().update(_real_pandas.__dict__)
