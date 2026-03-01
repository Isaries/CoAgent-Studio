"""
Neo4j Client — Async wrapper for Neo4j graph database operations.

Handles entity/relationship upsert, Leiden clustering, and subgraph traversal.
"""

from typing import Any, Dict, List, Optional

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import settings

logger = structlog.get_logger()


class Neo4jClient:
    """Async Neo4j client for GraphRAG operations."""

    def __init__(self) -> None:
        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """Initialize the Neo4j async driver."""
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        # Verify connectivity
        async with self._driver.session() as session:
            await session.run("RETURN 1")
        logger.info("neo4j_connected", uri=settings.NEO4J_URI)

    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()
            logger.info("neo4j_closed")

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        return self._driver

    # ── Entity Operations ──────────────────────────────────────────────

    async def upsert_entities(self, room_id: str, nodes: List[Dict[str, Any]]) -> int:
        """
        MERGE entities into the graph. Names are lowercased for consistency.
        If a node with the same name+room exists, its description is replaced.
        """
        query = """
        UNWIND $nodes AS node
        MERGE (n:Entity {name: toLower(node.name), room_id: $room_id})
        ON CREATE SET
            n.type = node.type,
            n.description = node.description,
            n.display_name = node.name,
            n.created_at = datetime()
        ON MATCH SET
            n.type = node.type,
            n.description = node.description,
            n.display_name = node.name,
            n.updated_at = datetime()
        RETURN count(n) AS cnt
        """
        async with self.driver.session() as session:
            result = await session.run(query, room_id=room_id, nodes=nodes)
            record = await result.single()
            return record["cnt"] if record else 0

    async def upsert_relationships(self, room_id: str, edges: List[Dict[str, Any]]) -> int:
        """
        MERGE relationships between entities. Names are lowercased.
        Creates source/target nodes if they don't exist yet (defensive).
        """
        query = """
        UNWIND $edges AS edge
        MERGE (a:Entity {name: toLower(edge.source), room_id: $room_id})
        MERGE (b:Entity {name: toLower(edge.target), room_id: $room_id})
        MERGE (a)-[r:RELATES_TO {relation: edge.relation}]->(b)
        ON CREATE SET
            r.evidence = edge.evidence,
            r.strength = edge.strength,
            r.created_at = datetime()
        ON MATCH SET
            r.evidence = edge.evidence,
            r.strength = CASE WHEN edge.strength > r.strength THEN edge.strength ELSE r.strength END,
            r.updated_at = datetime()
        RETURN count(r) AS cnt
        """
        async with self.driver.session() as session:
            result = await session.run(query, room_id=room_id, edges=edges)
            record = await result.single()
            return record["cnt"] if record else 0

    async def delete_room_graph(self, room_id: str) -> int:
        """
        Delete ALL entities and relationships for a room.
        Used before a full rebuild to prevent data duplication.
        """
        query = """
        MATCH (n:Entity {room_id: $room_id})
        DETACH DELETE n
        RETURN count(n) AS cnt
        """
        async with self.driver.session() as session:
            result = await session.run(query, room_id=room_id)
            record = await result.single()
            deleted = record["cnt"] if record else 0
            logger.info("neo4j_room_graph_deleted", room_id=room_id, deleted=deleted)
            return deleted

    # ── Community Detection ────────────────────────────────────────────

    async def run_leiden_clustering(self, room_id: str) -> int:
        """
        Run Leiden community detection on entities for a specific room.
        Returns the number of communities found.
        
        Requires Neo4j GDS plugin.
        """
        # 1. Create or replace an in-memory graph projection for this room
        project_query = """
        CALL gds.graph.project.cypher(
            $graph_name,
            'MATCH (n:Entity {room_id: $room_id}) RETURN id(n) AS id',
            'MATCH (a:Entity {room_id: $room_id})-[r:RELATES_TO]->(b:Entity {room_id: $room_id}) RETURN id(a) AS source, id(b) AS target',
            {parameters: {room_id: $room_id}}
        )
        """
        graph_name = f"graphrag_{room_id}"

        async with self.driver.session() as session:
            # Drop existing projection if any
            try:
                await session.run("CALL gds.graph.drop($name, false)", name=graph_name)
            except Exception:
                pass  # Graph doesn't exist yet

            try:
                await session.run(project_query, graph_name=graph_name, room_id=room_id)
            except Exception as e:
                logger.warning("gds_projection_failed", error=str(e), room_id=room_id)
                return 0

            # 2. Run Leiden (with guaranteed cleanup)
            try:
                leiden_query = """
                CALL gds.leiden.write($graph_name, {
                    writeProperty: 'community_id',
                    includeIntermediateCommunities: true
                })
                YIELD communityCount
                RETURN communityCount
                """
                result = await session.run(leiden_query, graph_name=graph_name)
                record = await result.single()
                community_count = record["communityCount"] if record else 0

                logger.info("leiden_complete", room_id=room_id, communities=community_count)
                return community_count
            finally:
                # 3. Always cleanup projection even if Leiden fails
                try:
                    await session.run("CALL gds.graph.drop($name, false)", name=graph_name)
                except Exception:
                    pass

    async def get_community_members(self, room_id: str, community_id: int) -> Dict[str, Any]:
        """Retrieve all entities and their relationships within a community."""
        query = """
        MATCH (n:Entity {room_id: $room_id, community_id: $community_id})
        OPTIONAL MATCH (n)-[r:RELATES_TO]-(m:Entity {room_id: $room_id, community_id: $community_id})
        RETURN
            collect(DISTINCT {name: n.display_name, type: n.type, description: n.description}) AS nodes,
            collect(DISTINCT {source: startNode(r).display_name, target: endNode(r).display_name, relation: r.relation, evidence: r.evidence}) AS edges
        """
        async with self.driver.session() as session:
            result = await session.run(query, room_id=room_id, community_id=community_id)
            record = await result.single()
            if record:
                return {"nodes": record["nodes"], "edges": record["edges"]}
            return {"nodes": [], "edges": []}

    async def get_distinct_communities(self, room_id: str) -> List[int]:
        """Get all distinct community IDs for a room."""
        query = """
        MATCH (n:Entity {room_id: $room_id})
        WHERE n.community_id IS NOT NULL
        RETURN DISTINCT n.community_id AS cid
        ORDER BY cid
        """
        async with self.driver.session() as session:
            result = await session.run(query, room_id=room_id)
            records = await result.data()
            return [r["cid"] for r in records]

    # ── Query Operations ───────────────────────────────────────────────

    async def get_local_subgraph(
        self, room_id: str, entity_names: List[str], depth: int = 2
    ) -> Dict[str, Any]:
        """
        Multi-hop traversal: start from named entities, expand `depth` hops.
        Returns nodes + edges for the subgraph.
        """
        query = """
        MATCH (start:Entity {room_id: $room_id})
        WHERE toLower(start.name) IN $names
        CALL apoc.path.subgraphAll(start, {maxLevel: $depth, relationshipFilter: 'RELATES_TO'})
        YIELD nodes, relationships
        WITH nodes, relationships
        UNWIND nodes AS n
        WITH collect(DISTINCT {
            id: elementId(n), name: n.display_name, type: n.type,
            description: n.description, community_id: n.community_id
        }) AS node_list, relationships
        UNWIND relationships AS r
        RETURN
            node_list AS nodes,
            collect(DISTINCT {
                source: startNode(r).display_name, target: endNode(r).display_name,
                relation: r.relation, evidence: r.evidence
            }) AS edges
        """
        async with self.driver.session() as session:
            result = await session.run(
                query, room_id=room_id,
                names=[n.lower() for n in entity_names],
                depth=depth,
            )
            record = await result.single()
            if record:
                return {"nodes": record["nodes"], "edges": record["edges"]}
            return {"nodes": [], "edges": []}

    async def get_full_graph(self, room_id: str) -> Dict[str, Any]:
        """Return the entire entity graph for a room (for visualization)."""
        query = """
        MATCH (n:Entity {room_id: $room_id})
        OPTIONAL MATCH (n)-[r:RELATES_TO]->(m:Entity {room_id: $room_id})
        WITH
            collect(DISTINCT {
                id: elementId(n), name: n.display_name, type: n.type,
                description: n.description, community_id: n.community_id
            }) AS nodes,
            collect(DISTINCT CASE WHEN r IS NOT NULL THEN {
                source: n.display_name, target: m.display_name,
                relation: r.relation, evidence: r.evidence
            } END) AS raw_edges
        RETURN nodes, [e IN raw_edges WHERE e IS NOT NULL] AS edges
        """
        async with self.driver.session() as session:
            result = await session.run(query, room_id=room_id)
            record = await result.single()
            if record:
                return {"nodes": record["nodes"], "edges": record["edges"]}
            return {"nodes": [], "edges": []}

    async def get_graph_stats(self, room_id: str) -> Dict[str, int]:
        """Return counts for nodes, edges, communities."""
        query = """
        MATCH (n:Entity {room_id: $room_id})
        OPTIONAL MATCH (n)-[r:RELATES_TO]->()
        RETURN
            count(DISTINCT n) AS node_count,
            count(DISTINCT r) AS edge_count,
            count(DISTINCT CASE WHEN n.community_id IS NOT NULL THEN n.community_id END) AS community_count
        """
        async with self.driver.session() as session:
            result = await session.run(query, room_id=room_id)
            record = await result.single()
            if record:
                return dict(record)
            return {"node_count": 0, "edge_count": 0, "community_count": 0}


# Module-level singleton
neo4j_client = Neo4jClient()
