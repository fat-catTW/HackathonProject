import tempfile
import threading
from pathlib import Path

import pytest

from backend.app.services import store as store_module


@pytest.fixture
def memory_store():
    with tempfile.TemporaryDirectory() as tmp:
        yield store_module.MemoryStore(storage_path=Path(tmp) / "store.json")


def test_get_sku_stock_defaults_to_zero_when_never_set(memory_store):
    assert memory_store.get_sku_stock("sku_never_seeded") == 0


def test_restock_then_get_sku_stock(memory_store):
    memory_store.restock_sku("sku_a", 10)
    assert memory_store.get_sku_stock("sku_a") == 10
    memory_store.restock_sku("sku_a", 5)
    assert memory_store.get_sku_stock("sku_a") == 15


def test_decrement_sku_stock_succeeds_when_enough_stock(memory_store):
    memory_store.restock_sku("sku_a", 10)
    assert memory_store.decrement_sku_stock("sku_a", 4) is True
    assert memory_store.get_sku_stock("sku_a") == 6


def test_decrement_sku_stock_fails_when_insufficient(memory_store):
    memory_store.restock_sku("sku_a", 3)
    assert memory_store.decrement_sku_stock("sku_a", 4) is False
    assert memory_store.get_sku_stock("sku_a") == 3  # unchanged on failure


def test_decrement_sku_stock_is_atomic_under_concurrent_calls(memory_store):
    memory_store.restock_sku("sku_a", 10)
    results = []

    def worker():
        results.append(memory_store.decrement_sku_stock("sku_a", 3))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 10 stock, 5 threads each asking for 3 (needs 15 total) -> exactly 3 succeed (9 taken), 2 fail
    assert results.count(True) == 3
    assert results.count(False) == 2
    assert memory_store.get_sku_stock("sku_a") == 1
