import traceback
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import inspect, text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.db import engine

router = APIRouter()

# Configuration for table relations
TABLE_RELATIONS = {
    "message": {
        "alias": "m",
        "select_extras": ", u.full_name as sender_name, r.name as room_name",
        "joins": 'LEFT JOIN "user" u ON m.sender_id = u.id LEFT JOIN "room" r ON m.room_id = r.id',
        "search_fields": ["u.full_name", "r.name"],
    },
    "course": {
        "alias": "c",
        "select_extras": ", u.full_name as owner_name",
        "joins": 'LEFT JOIN "user" u ON c.owner_id = u.id',
        "search_fields": ["u.full_name"],
    },
    "room": {
        "alias": "r",
        "select_extras": ", c.title as course_title",
        "joins": 'LEFT JOIN "course" c ON r.course_id = c.id',
        "search_fields": ["c.title"],
    },
    "usercourselink": {
        "alias": "l",
        "select_extras": ", u.email as user_email, c.title as course_title",
        "joins": 'LEFT JOIN "user" u ON l.user_id = u.id LEFT JOIN "course" c ON l.course_id = c.id',
        "search_fields": ["u.email", "c.title"],
    },
    "userroomlink": {
        "alias": "l",
        "select_extras": ", u.email as user_email, r.name as room_name",
        "joins": 'LEFT JOIN "user" u ON l.user_id = u.id LEFT JOIN "room" r ON l.room_id = r.id',
        "search_fields": ["u.email", "r.name"],
    },
}

# Fields to filter out from response for security
SENSITIVE_FIELDS = ["hashed_password", "salt", "api_key", "secret", "token"]


@router.get("/tables", response_model=List[str])
async def list_tables(
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    List all tables in the database.
    """
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    return tables


@router.get("/tables/{table_name}", response_model=List[Dict[str, Any]])
async def get_table_data(
    table_name: str,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    resolve_relations: bool = False,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    session: AsyncSession = Depends(deps.get_session),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Get data from a specific table.
    """
    try:
        async with engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            if table_name not in tables:
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

            columns = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_columns(table_name)
            )

        column_names = [c["name"] for c in columns]
        relation_config, alias = _get_relation_config(table_name, resolve_relations)

        # Build Query Parts
        select_part, join_part = _build_select_and_join(table_name, relation_config, alias)
        conditions, params = _build_conditions(
            columns, alias, search, start_date, end_date, relation_config
        )
        params.update({"limit": limit, "offset": offset})

        order_clause = _build_order_clause(column_names, alias)
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        final_query = text(
            f"{select_part} {join_part} {where_clause} {order_clause} LIMIT :limit OFFSET :offset"
        )

        result = await session.exec(final_query, params=params)
        data = result.mappings().all()

        return _filter_sensitive_data(data)

    except Exception as e:
        error_detail = f"{e!s}\n{traceback.format_exc()}"
        print(f"Error in get_table_data: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail) from e


def _get_relation_config(
    table_name: str, resolve_relations: bool
) -> tuple[Dict[str, Any] | None, str | None]:
    relation_config = TABLE_RELATIONS.get(table_name) if resolve_relations else None
    alias = relation_config["alias"] if relation_config else None
    return relation_config, alias


def _build_select_and_join(
    table_name: str, relation_config: Dict[str, Any] | None, alias: str | None
) -> tuple[str, str]:
    select_part = f'SELECT * FROM "{table_name}"'
    join_part = ""
    if relation_config:
        alias = relation_config["alias"]
        select_part = (
            f'SELECT {alias}.*{relation_config["select_extras"]} FROM "{table_name}" {alias}'
        )
        join_part = relation_config["joins"]
    return select_part, join_part


def _build_conditions(
    columns: List[Dict[str, Any]],
    alias: str | None,
    search: str | None,
    start_date: str | None,
    end_date: str | None,
    relation_config: Dict[str, Any] | None,
) -> tuple[List[str], Dict[str, Any]]:
    conditions = []
    params: Dict[str, Any] = {}

    if search:
        filters = _build_search_filters(columns, alias, relation_config)
        if filters:
            conditions.append("(" + " OR ".join(filters) + ")")
            params["search_pattern"] = f"%{search}%"

    if "created_at" in [c["name"] for c in columns]:
        col_created_at = f"{alias}.created_at" if alias else "created_at"
        if start_date:
            conditions.append(f"{col_created_at} >= :start_date")
            params["start_date"] = _parse_date(start_date)
        if end_date:
            conditions.append(f"{col_created_at} <= :end_date")
            params["end_date"] = _parse_date(end_date)

    return conditions, params


def _build_search_filters(
    columns: List[Dict[str, Any]],
    alias: str | None,
    relation_config: Dict[str, Any] | None,
) -> List[str]:
    search_filters = []
    for col in columns:
        c_name = col["name"]
        c_ref = f"{alias}.{c_name}" if alias else c_name

        if (
            c_name == "id"
            or c_name.endswith("_id")
            or "uuid" in str(col["type"]).lower()
            or c_name in ["role", "status"]
        ):
            search_filters.append(f"CAST({c_ref} AS TEXT) ILIKE :search_pattern")
        elif c_name in [
            "email",
            "username",
            "full_name",
            "title",
            "name",
            "content",
            "description",
            "caption",
        ]:
            search_filters.append(f"{c_ref} ILIKE :search_pattern")

    if relation_config and "search_fields" in relation_config:
        for field in relation_config["search_fields"]:
            search_filters.append(f"{field} ILIKE :search_pattern")

    return search_filters


def _parse_date(date_str: str) -> Any:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except ValueError:
        return date_str


def _build_order_clause(column_names: List[str], alias: str | None) -> str:
    if "created_at" in column_names:
        col_ref = f"{alias}.created_at" if alias else "created_at"
        return f"ORDER BY {col_ref} DESC"
    elif "id" in column_names:
        col_ref = f"{alias}.id" if alias else "id"
        return f"ORDER BY {col_ref} DESC"
    return ""


def _filter_sensitive_data(data: Any) -> List[Dict[str, Any]]:
    clean_data = []
    for row in data:
        row_dict = dict(row)
        for field in SENSITIVE_FIELDS:
            row_dict.pop(field, None)
        clean_data.append(row_dict)
    return clean_data
