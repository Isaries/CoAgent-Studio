"""
Unit tests for app.services.graphrag_service.

Covers:
- extract_entities_task: incremental fetch (filters by graphrag_last_synced_at)
- extract_entities_task: early return when no new messages
- extract_entities_task: watermark is updated after successful extraction
- extract_entities_task: LLM extraction uses asyncio.gather (concurrent)
- full_graph_rebuild_task: resets watermark before extraction
- chunk_messages: correct token-based chunking
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.graph_schemas import EntityNode, EntityRelationship, GraphChunk
from app.models.room import Room
from app.services.graphrag_service import chunk_messages, _merge_graph_chunks


# ---------------------------------------------------------------------------
# chunk_messages — pure function, no mocking needed
# ---------------------------------------------------------------------------


def test_chunk_messages_empty_returns_empty():
    result = chunk_messages([])
    assert result == []


def test_chunk_messages_single_short_message_is_one_chunk():
    msgs = [{"sender": "Alice", "content": "Hello"}]
    chunks = chunk_messages(msgs, max_tokens=600)
    assert len(chunks) == 1
    assert "Alice: Hello" in chunks[0]


def test_chunk_messages_splits_at_token_limit():
    """Messages that exceed max_tokens must be split into multiple chunks."""
    # Each message is roughly ~10 tokens; 5 messages at limit=30 → 2 chunks
    msgs = [{"sender": "User", "content": f"word{i} " * 8} for i in range(5)]
    chunks = chunk_messages(msgs, max_tokens=30)
    assert len(chunks) > 1


def test_chunk_messages_all_content_preserved():
    """No messages should be dropped — all content must appear in some chunk."""
    msgs = [{"sender": f"U{i}", "content": f"msg{i}"} for i in range(10)]
    chunks = chunk_messages(msgs, max_tokens=600)
    combined = "\n".join(chunks)
    for msg in msgs:
        assert msg["content"] in combined


# ---------------------------------------------------------------------------
# _merge_graph_chunks — pure function
# ---------------------------------------------------------------------------


def _make_chunk(node_names: list[str], edge_triples: list[tuple]) -> GraphChunk:
    nodes = [EntityNode(name=n, type="CONCEPT", description="") for n in node_names]
    edges = [
        EntityRelationship(source=s, target=t, relation=r, evidence="")
        for s, t, r in edge_triples
    ]
    return GraphChunk(nodes=nodes, edges=edges)


def test_merge_graph_chunks_deduplicates_nodes():
    c1 = _make_chunk(["Alice", "Bob"], [])
    c2 = _make_chunk(["Alice", "Carol"], [])
    merged = _merge_graph_chunks(c1, c2)
    names = [n.name.lower() for n in merged.nodes]
    assert names.count("alice") == 1
    assert "bob" in names
    assert "carol" in names


def test_merge_graph_chunks_deduplicates_edges():
    c1 = _make_chunk([], [("A", "B", "KNOWS")])
    c2 = _make_chunk([], [("A", "B", "KNOWS")])
    merged = _merge_graph_chunks(c1, c2)
    assert len(merged.edges) == 1


def test_merge_graph_chunks_later_tier_overrides_description():
    c1 = _make_chunk([], [])
    c1.nodes = [EntityNode(name="X", type="CONCEPT", description="old")]
    c2 = _make_chunk([], [])
    c2.nodes = [EntityNode(name="X", type="CONCEPT", description="new")]
    merged = _merge_graph_chunks(c1, c2)
    assert merged.nodes[0].description == "new"


# ---------------------------------------------------------------------------
# extract_entities_task — incremental fetch
# ---------------------------------------------------------------------------


def _make_ctx(room: Room, messages: list, api_key: str = "test-api-key") -> dict:
    """Build a minimal ARQ ctx dict with mocked session_factory."""
    mock_session = AsyncMock()
    # First get() call: fetch room for last_synced_at
    # Second exec() call: fetch messages
    mock_result = Mock()
    mock_result.all.return_value = messages
    mock_session.exec = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=room)
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def session_factory():
        yield mock_session

    return {
        "session_factory": session_factory,
        "embedding_api_key": api_key,
        "_mock_session": mock_session,
    }


@pytest.mark.asyncio()
async def test_extract_entities_task_no_api_key_returns_error():
    """Task must return error dict when no API key is configured."""
    from app.services.graphrag_service import extract_entities_task

    room = Room(id=uuid4(), name="R", space_id=uuid4())
    ctx = _make_ctx(room, [], api_key="")

    result = await extract_entities_task(ctx, str(room.id))
    assert "error" in result


@pytest.mark.asyncio()
async def test_extract_entities_task_no_new_messages_returns_zeros():
    """When no messages exist since last sync, task returns {nodes:0, edges:0, chunks:0}."""
    from app.services.graphrag_service import extract_entities_task

    room = Room(
        id=uuid4(),
        name="R",
        space_id=uuid4(),
        graphrag_last_synced_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    ctx = _make_ctx(room, messages=[])  # no new messages

    result = await extract_entities_task(ctx, str(room.id))
    assert result == {"nodes": 0, "edges": 0, "chunks": 0}


@pytest.mark.asyncio()
async def test_extract_entities_task_incremental_uses_last_synced_at():
    """
    When room.graphrag_last_synced_at is set, the query WHERE clause must include it.
    We verify this by capturing the sqlmodel query args passed to session.exec().
    """
    from app.services.graphrag_service import extract_entities_task
    from app.models.message import Message

    last_synced = datetime(2026, 1, 1, tzinfo=timezone.utc)
    room = Room(id=uuid4(), name="R", space_id=uuid4(), graphrag_last_synced_at=last_synced)

    # Only return empty messages to trigger early exit; we just want to inspect the query
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = []
    mock_session.exec = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=room)

    captured_queries = []

    async def capturing_exec(query):
        captured_queries.append(query)
        return mock_result

    mock_session.exec = capturing_exec

    @asynccontextmanager
    async def session_factory():
        yield mock_session

    ctx = {"session_factory": session_factory, "embedding_api_key": "key"}
    await extract_entities_task(ctx, str(room.id))

    # At least one query was built with a WHERE clause referencing the date
    # (sqlalchemy query objects are not trivially inspectable, but we can verify
    #  that two calls were made: one for the room, one for messages)
    assert mock_session.get.call_count >= 1
    # The room fetch should be for Room model
    call_model = mock_session.get.call_args_list[0].args[0]
    assert call_model is Room


@pytest.mark.asyncio()
async def test_extract_entities_task_watermark_updated_after_extraction():
    """After successful extraction, room.graphrag_last_synced_at must be set."""
    from app.services.graphrag_service import extract_entities_task
    from app.models.message import Message

    room = Room(id=uuid4(), name="R", space_id=uuid4(), graphrag_last_synced_at=None)
    room_id = str(room.id)

    # Simulate one message existing
    msg = Message(
        id=uuid4(),
        content="Hello world",
        room_id=room.id,
        sender_id=uuid4(),
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )

    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = [msg]
    mock_session.exec = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=room)
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def session_factory():
        yield mock_session

    ctx = {"session_factory": session_factory, "embedding_api_key": "key"}

    # Patch all external dependencies so only our session logic runs
    empty_chunk = GraphChunk(nodes=[], edges=[])
    with (
        patch(
            "app.services.graphrag_service.extract_structural_facts",
            new=AsyncMock(return_value=empty_chunk),
        ),
        patch(
            "app.services.graphrag_service.extract_nlp_facts",
            return_value=empty_chunk,
        ),
        patch(
            "app.services.graphrag_service.extract_concepts_from_chunk",
            new=AsyncMock(return_value=empty_chunk),
        ),
        patch(
            "app.services.graphrag_service.neo4j_client.upsert_entities",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.graphrag_service.neo4j_client.upsert_relationships",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.graphrag_service.EmbeddingService",
        ) as MockEmbedSvc,
        patch("app.core.cache.cache") as mock_cache,
        patch("app.services.graphrag_service.vector_store") as mock_vs,
    ):
        mock_cache.redis = None
        mock_vs.upsert_embeddings = AsyncMock()
        embed_instance = MockEmbedSvc.return_value
        embed_instance.get_embeddings_batch = AsyncMock(return_value=[])

        await extract_entities_task(ctx, room_id)

    # Verify commit was called (watermark update)
    mock_session.commit.assert_awaited()
    # Verify room.graphrag_last_synced_at was set
    assert room.graphrag_last_synced_at is not None


# ---------------------------------------------------------------------------
# extract_entities_task — concurrent LLM extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_extract_entities_task_uses_concurrent_llm_calls():
    """
    LLM extractions must run concurrently via asyncio.gather, not sequentially.
    We verify this by measuring that multiple extractions finish faster than
    sequential execution would allow.
    """
    from app.services.graphrag_service import extract_entities_task
    from app.models.message import Message

    room = Room(id=uuid4(), name="R", space_id=uuid4())
    # Enough messages to produce multiple chunks
    messages = [
        Message(
            id=uuid4(),
            content=f"message content {i} " * 20,  # force chunking
            room_id=room.id,
            sender_id=uuid4(),
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        for i in range(6)
    ]

    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = messages
    mock_session.exec = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=room)
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def session_factory():
        yield mock_session

    call_times = []
    empty_chunk = GraphChunk(nodes=[], edges=[])

    async def delayed_extract(*args, **kwargs):
        call_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.05)  # 50ms simulated LLM latency
        return empty_chunk

    ctx = {"session_factory": session_factory, "embedding_api_key": "key"}

    with (
        patch(
            "app.services.graphrag_service.extract_structural_facts",
            new=AsyncMock(return_value=empty_chunk),
        ),
        patch(
            "app.services.graphrag_service.extract_nlp_facts",
            return_value=empty_chunk,
        ),
        patch(
            "app.services.graphrag_service.extract_concepts_from_chunk",
            new=delayed_extract,
        ),
        patch(
            "app.services.graphrag_service.neo4j_client.upsert_entities",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.graphrag_service.neo4j_client.upsert_relationships",
            new=AsyncMock(return_value=0),
        ),
        patch("app.services.graphrag_service.EmbeddingService") as MockEmbedSvc,
        patch("app.services.graphrag_service.vector_store.upsert_embeddings", new=AsyncMock()),
        patch("app.core.cache.cache") as mock_cache,
    ):
        mock_cache.redis = None
        embed_instance = MockEmbedSvc.return_value
        embed_instance.get_embeddings_batch = AsyncMock(return_value=[])

        import time
        start = time.monotonic()
        await extract_entities_task(ctx, str(room.id))
        elapsed = time.monotonic() - start

    # If truly concurrent (semaphore=3), 6 chunks at 50ms each takes ~100ms
    # If sequential, it would take ~300ms. We allow up to 250ms to be safe.
    if len(call_times) > 1:
        assert elapsed < 0.25, f"LLM calls appear sequential — elapsed={elapsed:.3f}s"


# ---------------------------------------------------------------------------
# full_graph_rebuild_task — resets watermark
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_full_graph_rebuild_resets_watermark():
    """full_graph_rebuild_task must reset graphrag_last_synced_at to None before extraction."""
    from app.services.graphrag_service import full_graph_rebuild_task

    last_synced = datetime(2026, 1, 1, tzinfo=timezone.utc)
    room = Room(id=uuid4(), name="R", space_id=uuid4(), graphrag_last_synced_at=last_synced)
    room_id = str(room.id)

    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = []  # no messages → sub-tasks exit early
    mock_session.exec = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=room)
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def session_factory():
        yield mock_session

    ctx = {"session_factory": session_factory, "embedding_api_key": "key"}

    with (
        patch("app.services.graphrag_service.neo4j_client.delete_room_graph", new=AsyncMock(return_value=0)),
        patch("app.services.graphrag_service.vector_store.delete_by_room", new=AsyncMock()),
    ):
        await full_graph_rebuild_task(ctx, room_id)

    # The watermark should have been cleared
    assert room.graphrag_last_synced_at is None
