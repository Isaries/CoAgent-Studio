from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, inspect
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.db import engine

router = APIRouter()

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
    session: AsyncSession = Depends(deps.get_session),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Get data from a specific table.
    """
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    
    if table_name not in tables:
         raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    # Safe to use table_name in query since we validated it against existing tables
    query = text(f'SELECT * FROM "{table_name}" LIMIT :limit OFFSET :offset')
    try:
        result = await session.exec(query, params={"limit": limit, "offset": offset})
        data = result.mappings().all()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
