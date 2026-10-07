import sqlglot
from sqlglot import exp

# Permitted read-only root expression types
ALLOWED_ROOT_TYPES = (
    exp.Select,
    exp.Union
)

# Forbidden DDL and DML operations that mutate database state
FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.TruncateTable
)

def validate_and_sanitize_sql(sql_query: str, max_limit: int = 100) -> str:
    """
    Validates that a generated SQL statement is purely read-only, 
    structurally safe, and bounded by a maximum row limit.

    Args:
        sql_query: Raw SQL query text.
        max_limit: Upper bound limit for returned rows.

    Returns:
        Sanitized SQL query formatted for SQLite execution.

    Raises:
        ValueError: If query violates security policies or contains invalid syntax.
    """
    cleaned_query = sql_query.strip().rstrip(";")
    
    try:
        # Parse query string into an AST using SQLite dialect
        parsed_expressions = sqlglot.parse(cleaned_query, read="sqlite")
    except Exception as e:
        raise ValueError(f"Syntax Error: Failed to parse SQL query. Details: {str(e)}")

    if not parsed_expressions:
        raise ValueError("Security Violation: Received an empty SQL query.")

    # Guard 1: Block multi-statement execution to prevent chained injections
    if len(parsed_expressions) > 1:
        raise ValueError("Security Violation: Chained queries (multiple statements) are prohibited.")

    expression = parsed_expressions[0]

    # Guard 2: Enforce root operation is strictly a SELECT or UNION
    if not isinstance(expression, ALLOWED_ROOT_TYPES):
        raise ValueError(f"Security Violation: Non-SELECT operation attempted: {type(expression).__name__}")

    # Guard 3: Deep AST scan to detect nested mutations (e.g. CTE with DELETE)
    for node in expression.walk():
        if isinstance(node, FORBIDDEN_EXPRESSIONS):
            raise ValueError(f"Security Violation: Mutating clause detected: {type(node).__name__}")

    # Guard 4: Enforce an execution row limit to prevent memory overloads
    limit_node = expression.find(exp.Limit)
    if not limit_node:
        expression = expression.limit(max_limit)
    else:
        current_limit_val = int(limit_node.expression.name)
        if current_limit_val > max_limit:
            limit_node.set("expression", exp.Literal.number(max_limit))

    return expression.sql(dialect="sqlite")


if __name__ == "__main__":
    # Test suite to evaluate guardrail behavior
    test_cases = [
        ("SELECT * FROM fact_shipments", True),
        ("DELETE FROM dim_hubs WHERE hub_id = 'HUB_RUH_01'", False),
        ("SELECT * FROM fact_shipments; DROP TABLE dim_couriers;", False),
        ("SELECT hub_id, COUNT(*) FROM fact_shipments GROUP BY hub_id LIMIT 500", True),
    ]

    print("--- Running Guardrail Verification Tests ---")
    for query, should_pass in test_cases:
        try:
            sanitized = validate_and_sanitize_sql(query, max_limit=100)
            status = "PASSED" if should_pass else "UNEXPECTED SUCCESS"
            print(f"[{status}] Original: {query}\n -> Output: {sanitized}\n")
        except ValueError as err:
            status = "BLOCKED (Safe)" if not should_pass else "FALSE POSITIVE"
            print(f"[{status}] Original: {query}\n -> Reason: {err}\n")


def is_logistics_query(prompt: str) -> bool:
    """
    Checks if the user prompt is relevant to the logistics & analytics domain.
    Returns False if the query is clearly off-topic (e.g., general trivia, weather, etc.).
    """
    
    off_topic_triggers = [
        "عاصمة", "الطقس", "رئيس", "ترجم", "قصيدة", "نكتة", "وصفة", "شعر", "علاج",
        "capital", "weather", "president", "translate", "joke", "poem", "recipe"
    ]
    
    prompt_lower = prompt.lower().strip()
    
    
    for trigger in off_topic_triggers:
        if trigger in prompt_lower:
            return False
            
    return True