from astraforge.memory.store import MemoryStore


def test_memory_roundtrip(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    store.remember("pattern", "fastapi-health", {"recommendation": "keep health endpoint simple"})
    results = store.recall(kind="pattern", query="health")
    assert len(results) == 1
    assert "fastapi" in results[0]["key"]


def test_semantic_recall_ranks_similar_vectors(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    store.remember("pattern", "api", {"recommendation": "use health checks"}, embedding=[1.0, 0.0])
    store.remember("pattern", "database", {"recommendation": "use indexes"}, embedding=[0.0, 1.0])
    results = store.semantic_recall([0.9, 0.1], kind="pattern")
    assert results[0]["key"] == "api"
    assert results[0]["score"] > results[1]["score"]
