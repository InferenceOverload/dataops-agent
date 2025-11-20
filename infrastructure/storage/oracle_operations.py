"""
Oracle Database Operations

Provides utilities for connecting to Oracle databases and fetching PL/SQL source code.

This module uses oracledb (the modern successor to cx_Oracle) for database connectivity.
"""

import os
from typing import Optional

try:
    import oracledb
except ImportError:
    oracledb = None  # Optional dependency for local testing


def get_oracle_connection():
    """
    Create and return an Oracle database connection.

    Reads connection parameters from environment variables:
    - ORACLE_DSN: Database connection string (host:port/service_name)
    - ORACLE_USER: Database username
    - ORACLE_PASSWORD: Database password

    Returns:
        oracledb.Connection: Active database connection

    Raises:
        ValueError: If required environment variables are missing
        oracledb.DatabaseError: If connection fails

    Example:
        conn = get_oracle_connection()
        try:
            # Use connection
            pass
        finally:
            conn.close()
    """
    dsn = os.getenv("ORACLE_DSN")
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")

    if not dsn:
        raise ValueError("ORACLE_DSN environment variable is not set")
    if not user:
        raise ValueError("ORACLE_USER environment variable is not set")
    if not password:
        raise ValueError("ORACLE_PASSWORD environment variable is not set")

    try:
        connection = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        return connection
    except oracledb.DatabaseError as e:
        raise oracledb.DatabaseError(f"Failed to connect to Oracle database: {e}")


def get_package_source(schema: str, package: str) -> str:
    """
    Retrieve the full PL/SQL source code for a package.

    Fetches both package specification and body from ALL_SOURCE,
    concatenating them in the correct order.

    Args:
        schema: Schema/owner name (e.g., "BILLING")
        package: Package name (e.g., "PKG_POLICY_BILLING")

    Returns:
        str: Complete package source code (spec + body)

    Raises:
        ValueError: If package not found or schema/package is invalid
        oracledb.DatabaseError: If database query fails

    Example:
        source = get_package_source("BILLING", "PKG_POLICY_BILLING")
    """
    if not schema or not package:
        raise ValueError("Schema and package name are required")

    schema = schema.upper()
    package = package.upper()

    conn = get_oracle_connection()
    try:
        cursor = conn.cursor()

        # Query to fetch package source ordered by type (spec first, then body) and line number
        query = """
            SELECT TEXT
            FROM ALL_SOURCE
            WHERE OWNER = :schema
              AND NAME = :package
              AND TYPE IN ('PACKAGE', 'PACKAGE BODY')
            ORDER BY
              CASE TYPE
                WHEN 'PACKAGE' THEN 1
                WHEN 'PACKAGE BODY' THEN 2
              END,
              LINE
        """

        cursor.execute(query, schema=schema, package=package)
        rows = cursor.fetchall()

        if not rows:
            raise ValueError(
                f"Package {schema}.{package} not found. "
                f"Verify the schema and package name are correct and you have access."
            )

        # Concatenate all lines
        source = "".join(row[0] for row in rows)
        return source

    finally:
        conn.close()


def get_view_definition(schema: str, view_name: str) -> str:
    """
    Retrieve the CREATE VIEW definition for a view.

    Fetches the view definition from ALL_VIEWS.

    Args:
        schema: Schema/owner name (e.g., "BILLING")
        view_name: View name (e.g., "VW_ACTIVE_CUSTOMERS")

    Returns:
        str: CREATE VIEW SQL statement

    Raises:
        ValueError: If view not found or schema/view_name is invalid
        oracledb.DatabaseError: If database query fails

    Example:
        definition = get_view_definition("BILLING", "VW_ACTIVE_CUSTOMERS")
    """
    if not schema or not view_name:
        raise ValueError("Schema and view name are required")

    schema = schema.upper()
    view_name = view_name.upper()

    conn = get_oracle_connection()
    try:
        cursor = conn.cursor()

        query = """
            SELECT TEXT
            FROM ALL_VIEWS
            WHERE OWNER = :schema
              AND VIEW_NAME = :view_name
        """

        cursor.execute(query, schema=schema, view_name=view_name)
        row = cursor.fetchone()

        if not row:
            raise ValueError(
                f"View {schema}.{view_name} not found. "
                f"Verify the schema and view name are correct and you have access."
            )

        # Construct full CREATE VIEW statement
        view_text = row[0]
        return f"CREATE OR REPLACE VIEW {schema}.{view_name} AS\n{view_text}"

    finally:
        conn.close()


def get_trigger_source(schema: str, trigger_name: str) -> str:
    """
    Retrieve the source code for a trigger.

    Fetches trigger definition from ALL_TRIGGERS and optionally ALL_SOURCE.

    Args:
        schema: Schema/owner name (e.g., "BILLING")
        trigger_name: Trigger name (e.g., "TRG_UPDATE_TIMESTAMP")

    Returns:
        str: Trigger source code

    Raises:
        ValueError: If trigger not found or schema/trigger_name is invalid
        oracledb.DatabaseError: If database query fails

    Example:
        source = get_trigger_source("BILLING", "TRG_UPDATE_TIMESTAMP")
    """
    if not schema or not trigger_name:
        raise ValueError("Schema and trigger name are required")

    schema = schema.upper()
    trigger_name = trigger_name.upper()

    conn = get_oracle_connection()
    try:
        cursor = conn.cursor()

        # First try to get from ALL_SOURCE (more detailed)
        query_source = """
            SELECT TEXT
            FROM ALL_SOURCE
            WHERE OWNER = :schema
              AND NAME = :trigger_name
              AND TYPE = 'TRIGGER'
            ORDER BY LINE
        """

        cursor.execute(query_source, schema=schema, trigger_name=trigger_name)
        rows = cursor.fetchall()

        if rows:
            # Concatenate all lines from ALL_SOURCE
            source = "".join(row[0] for row in rows)
            return source

        # Fallback to ALL_TRIGGERS if not in ALL_SOURCE
        query_triggers = """
            SELECT TRIGGER_TYPE, TRIGGERING_EVENT, TABLE_OWNER, TABLE_NAME, TRIGGER_BODY
            FROM ALL_TRIGGERS
            WHERE OWNER = :schema
              AND TRIGGER_NAME = :trigger_name
        """

        cursor.execute(query_triggers, schema=schema, trigger_name=trigger_name)
        row = cursor.fetchone()

        if not row:
            raise ValueError(
                f"Trigger {schema}.{trigger_name} not found. "
                f"Verify the schema and trigger name are correct and you have access."
            )

        trigger_type, triggering_event, table_owner, table_name, trigger_body = row

        # Construct trigger definition
        source = f"""CREATE OR REPLACE TRIGGER {schema}.{trigger_name}
{trigger_type} {triggering_event} ON {table_owner}.{table_name}
{trigger_body}
"""
        return source

    finally:
        conn.close()


def test_oracle_connection() -> bool:
    """
    Test Oracle database connectivity.

    Returns:
        bool: True if connection successful, False otherwise

    Example:
        if test_oracle_connection():
            print("Oracle connection OK")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
        conn.close()
        return True
    except Exception as e:
        print(f"Oracle connection test failed: {e}")
        return False
