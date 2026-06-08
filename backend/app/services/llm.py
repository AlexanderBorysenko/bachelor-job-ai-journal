"""Per-task model/effort helpers for Claude calls."""


def output_config(effort: str = "", schema: dict | None = None) -> dict:
    """Build the ``messages.create(**kwargs)`` fragment for effort and/or
    structured outputs.

    Returns an ``extra_body`` dict carrying ``output_config`` (effort and/or the
    json_schema ``format``), or ``{}`` when neither is set. Passed via
    ``extra_body`` so it works on ``anthropic==0.52.0`` with no SDK upgrade.
    Effort errors on Haiku — pass ``effort=""`` for Haiku tasks.
    """
    cfg: dict = {}
    if effort:
        cfg["effort"] = effort
    if schema is not None:
        cfg["format"] = {"type": "json_schema", "schema": schema}
    if not cfg:
        return {}
    return {"extra_body": {"output_config": cfg}}
