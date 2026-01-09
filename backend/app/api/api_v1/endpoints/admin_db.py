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
    'message': {
        'alias': 'm',
        'select_extras': ', u.full_name as sender_name, r.name as room_name',
        'joins': 'LEFT JOIN "user" u ON m.sender_id = u.id LEFT JOIN "room" r ON m.room_id = r.id',
        'search_fields': ['u.full_name', 'r.name']
    },
    'course': {
        'alias': 'c',
        'select_extras': ', u.full_name as owner_name',
        'joins': 'LEFT JOIN "user" u ON c.owner_id = u.id',
        'search_fields': ['u.full_name']
    },
    'room': {
        'alias': 'r',
        'select_extras': ', c.title as course_title',
        'joins': 'LEFT JOIN "course" c ON r.course_id = c.id',
        'search_fields': ['c.title']
    },
    'usercourselink': {
        'alias': 'l',
        'select_extras': ', u.email as user_email, c.title as course_title',
        'joins': 'LEFT JOIN "user" u ON l.user_id = u.id LEFT JOIN "course" c ON l.course_id = c.id',
        'search_fields': ['u.email', 'c.title']
    },
    'userroomlink': {
        'alias': 'l',
        'select_extras': ', u.email as user_email, r.name as room_name',
        'joins': 'LEFT JOIN "user" u ON l.user_id = u.id LEFT JOIN "room" r ON l.room_id = r.id',
        'search_fields': ['u.email', 'r.name']
    },
}

# Fields to filter out from response for security
SENSITIVE_FIELDS = ['hashed_password', 'salt', 'api_key', 'secret', 'token']

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

        # Get columns to determine sorting
        async with engine.connect() as conn:
            columns = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_columns(table_name))
            column_names = [c['name'] for c in columns]

        # Determine Alias and Relation Config
        relation_config = TABLE_RELATIONS.get(table_name) if resolve_relations else None
        alias = relation_config['alias'] if relation_config else None

        # Build ORDER BY clause
        order_clause = ""
        if 'created_at' in column_names:
            col_ref = f"{alias}.created_at" if alias else "created_at"
            order_clause = f'ORDER BY {col_ref} DESC'
        elif 'id' in column_names:
            col_ref = f"{alias}.id" if alias else "id"
            order_clause = f'ORDER BY {col_ref} DESC'

        # Build WHERE clause components
        conditions = []
        params = {"limit": limit, "offset": offset}

        select_part = f'SELECT * FROM "{table_name}"'
        join_part = ""

        # Apply Relation Config
        if relation_config:
            alias = relation_config['alias']
            # We must alias the table in FROM to match the alias used everywhere else
            select_part = f'SELECT {alias}.*{relation_config["select_extras"]} FROM "{table_name}" {alias}'
            join_part = relation_config['joins']

        # Unified Search Logic (Global Partial Match)
        if search:
            search_filters = []
            params['search_pattern'] = f"%{search}%"

            # 1. Main Table Columns
            for col in columns:
                c_name = col['name']
                c_ref = f"{alias}.{c_name}" if alias else c_name

                # Check for ID/UUID columns or ENUMs (role, status)
                if c_name == 'id' or c_name.endswith('_id') or 'uuid' in str(col['type']).lower() or c_name in ['role', 'status']:
                     search_filters.append(f"CAST({c_ref} AS TEXT) ILIKE :search_pattern")
                # Check for Text columns
                elif c_name in ['email', 'username', 'full_name', 'title', 'name', 'content', 'description', 'caption']:
                     search_filters.append(f"{c_ref} ILIKE :search_pattern")

            # 2. Joined Columns (from config)
            if relation_config and 'search_fields' in relation_config:
                for field in relation_config['search_fields']:
                    search_filters.append(f"{field} ILIKE :search_pattern")

            if search_filters:
                conditions.append("(" + " OR ".join(search_filters) + ")")

        # 2. Date Filtering Logic (Appends to conditions)
        if 'created_at' in column_names:
            col_created_at = f"{alias}.created_at" if alias else "created_at"
            if start_date:
                conditions.append(f"{col_created_at} >= :start_date")
                try:
                    dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    params['start_date'] = dt.replace(tzinfo=None)
                except ValueError:
                    params['start_date'] = start_date

            if end_date:
                conditions.append(f"{col_created_at} <= :end_date")
                try:
                    dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    params['end_date'] = dt.replace(tzinfo=None)
                except ValueError:
                    params['end_date'] = end_date

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        final_query = f"{select_part} {join_part} {where_clause} {order_clause} LIMIT :limit OFFSET :offset"
        query = text(final_query)

        result = await session.exec(query, params=params)
        data = result.mappings().all()

        # Filter sensitive fields
        clean_data = []
        for row in data:
            row_dict = dict(row)
            for field in SENSITIVE_FIELDS:
                row_dict.pop(field, None)
            clean_data.append(row_dict)

        return clean_data

    except Exception as e:
        error_detail = f"{e!s}\n{traceback.format_exc()}"
        print(f"Error in get_table_data: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)
