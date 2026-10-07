import pytest
from src.guardrails import validate_and_sanitize_sql

def test_valid_select_query():
    """Verify that a standard SELECT query is accepted and sanitized with default LIMIT."""
    raw_sql = "SELECT * FROM fact_shipments WHERE is_sla_breached = 1"
    sanitized = validate_and_sanitize_sql(raw_sql)
    assert "LIMIT 100" in sanitized
    assert sanitized.startswith("SELECT")

def test_preserve_existing_limit():
    """Ensure that explicitly set LIMIT clause is preserved."""
    raw_sql = "SELECT courier_name FROM dim_couriers LIMIT 5"
    sanitized = validate_and_sanitize_sql(raw_sql)
    assert "LIMIT 5" in sanitized
    assert "LIMIT 100" not in sanitized

def test_block_drop_table():
    """Verify that DROP TABLE statements are strictly blocked."""
    raw_sql = "DROP TABLE fact_shipments;"
    with pytest.raises(ValueError):
        validate_and_sanitize_sql(raw_sql)

def test_block_delete_statement():
    """Verify that DELETE statements are blocked."""
    raw_sql = "DELETE FROM dim_couriers WHERE courier_id = 'CR_SPDX';"
    with pytest.raises(ValueError):
        validate_and_sanitize_sql(raw_sql)

def test_block_update_statement():
    """Verify that UPDATE statements are blocked."""
    raw_sql = "UPDATE dim_hubs SET city = 'Riyadh';"
    with pytest.raises(ValueError):
        validate_and_sanitize_sql(raw_sql)

def test_block_stacked_queries():
    """Ensure multi-statement injection attempts are blocked."""
    raw_sql = "SELECT * FROM dim_hubs; DROP TABLE dim_hubs;"
    with pytest.raises(ValueError):
        validate_and_sanitize_sql(raw_sql)