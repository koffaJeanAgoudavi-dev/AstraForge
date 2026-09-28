from astraforge.memory.store import MemoryStore


def test_memory_roundtrip(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    store.remember("pattern", "fastapi-health", {"recommendation": "keep health endpoint simple"})
    results = store.recall(kind="pattern", query="health")
    assert len(results) == 1
    assert "fastapi" in results[0]["key"]
