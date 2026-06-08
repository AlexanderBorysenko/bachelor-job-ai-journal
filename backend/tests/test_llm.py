from app.services.llm import output_config


def test_empty_when_nothing():
    assert output_config() == {}


def test_effort_only():
    assert output_config(effort="low") == {"extra_body": {"output_config": {"effort": "low"}}}


def test_schema_only():
    out = output_config(schema={"type": "object"})
    assert out == {"extra_body": {"output_config": {"format": {"type": "json_schema", "schema": {"type": "object"}}}}}


def test_both():
    cfg = output_config(effort="medium", schema={"type": "object"})["extra_body"]["output_config"]
    assert cfg["effort"] == "medium"
    assert cfg["format"]["type"] == "json_schema"
