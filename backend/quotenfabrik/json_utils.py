"""JSON helpers: PostgreSQL rejects NaN/Infinity in JSON(B), and numpy scalars are not JSON-serialisable."""

import json
import math


def json_safe(value):
    """Nested dicts/lists/tuples with non-finite floats (NaN, ±inf) as ``None`` and numpy scalars / arrays as
    plain Python values."""
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [json_safe(v) for v in value]
    if hasattr(value, "tolist") and not isinstance(value, str):  # numpy scalar or array
        return json_safe(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def dumps(value) -> str:
    """JSON for JSONB columns (engine-wide serializer): non-finite floats become null instead of an error."""
    return json.dumps(json_safe(value), allow_nan=False)
