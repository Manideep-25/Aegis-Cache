"""
aegiscache/tests/test_eviction.py
──────────────────────────────────
Unit tests for the three L1 eviction strategies and CacheManager.

Run:
    pytest aegiscache/tests/test_eviction.py -v
"""

from __future__ import annotations

import asyncio
import sys
import os

# Allow running from the project root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from aegiscache.cache.eviction import FIFOCache, LFUCache, LRUCache
from aegiscache.cache.manager import CacheManager, EventKind, Policy


class TestLRUCache:
    def test_basic_put_get(self):
        c = LRUCache(3)
        c.put("a", 1)
        assert c.get("a") == 1

    def test_miss_returns_none(self):
        c = LRUCache(3)
        assert c.get("nonexistent") is None

    def test_evicts_lru_entry(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.get("a")         
        evicted = c.put("c", 3)
        assert evicted == "b"
        assert c.get("b") is None
        assert c.get("a") == 1
        assert c.get("c") == 3

    def test_update_promotes_to_mru(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("a", 99)    
        evicted = c.put("c", 3)
        assert evicted == "b"
        assert c.get("a") == 99

    def test_capacity_one(self):
        c = LRUCache(1)
        c.put("x", 10)
        evicted = c.put("y", 20)
        assert evicted == "x"
        assert c.get("x") is None
        assert c.get("y") == 20

    def test_delete(self):
        c = LRUCache(3)
        c.put("a", 1)
        assert c.delete("a") is True
        assert c.delete("a") is False
        assert c.get("a") is None

    def test_size_tracks_correctly(self):
        c = LRUCache(5)
        for i in range(5):
            c.put(str(i), i)
        assert c.size() == 5
        c.delete("0")
        assert c.size() == 4

    def test_clear(self):
        c = LRUCache(4)
        c.put("a", 1)
        c.put("b", 2)
        c.clear()
        assert c.size() == 0
        assert c.get("a") is None

    def test_stats_hit_rate(self):
        c = LRUCache(4)
        c.put("k", "v")
        c.get("k")    
        c.get("k")    
        c.get("x")    
        s = c.stats
        assert s["hits"]   == 2
        assert s["misses"] == 1
        assert abs(s["hit_rate"] - 2/3) < 1e-3 

    def test_no_eviction_within_capacity(self):
        c = LRUCache(10)
        for i in range(10):
            evicted = c.put(str(i), i)
            assert evicted is None


class TestLFUCache:
    def test_basic_put_get(self):
        c = LFUCache(3)
        c.put("a", 10)
        assert c.get("a") == 10

    def test_evicts_least_frequent(self):
        c = LFUCache(2)
        c.put("a", 1)  
        c.put("b", 2)   
        c.get("a")       
        evicted = c.put("c", 3)
        assert evicted == "b"
        assert c.get("b") is None
        assert c.get("a") == 1
        assert c.get("c") == 3

    def test_fifo_tiebreak_within_frequency(self):
        """
        When two keys share the same frequency the oldest-inserted one
        should be evicted first.
        """
        c = LFUCache(2)
        c.put("first", 1)
        c.put("second", 2)
        evicted = c.put("third", 3)
        assert evicted == "first"

    def test_update_preserves_frequency_tracking(self):
        c = LFUCache(2)
        c.put("a", 1)    
        c.put("b", 2)   
        c.get("a")       
        c.put("a", 99)  
        evicted = c.put("c", 3)
        assert evicted == "b"

    def test_delete(self):
        c = LFUCache(3)
        c.put("z", 0)
        c.get("z")
        assert c.delete("z") is True
        assert c.delete("z") is False
        assert c.get("z") is None

    def test_clear(self):
        c = LFUCache(4)
        c.put("x", 1)
        c.clear()
        assert c.size() == 0

    def test_size(self):
        c = LFUCache(5)
        for i in range(5):
            c.put(f"k{i}", i)
        assert c.size() == 5


class TestFIFOCache:
    def test_basic_put_get(self):
        c = FIFOCache(3)
        c.put("a", 1)
        assert c.get("a") == 1

    def test_evicts_first_inserted(self):
        c = FIFOCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.get("a")         
        evicted = c.put("c", 3)
        assert evicted == "a"
        assert c.get("a") is None

    def test_update_does_not_change_eviction_order(self):
        c = FIFOCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("a", 999)     
        evicted = c.put("c", 3)
        assert evicted == "a"  

    def test_delete_and_reinsert(self):
        c = FIFOCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.delete("a")
        c.put("a", 1)  
        evicted = c.put("c", 3)
        assert evicted == "b"

    def test_clear(self):
        c = FIFOCache(4)
        c.put("x", 1)
        c.clear()
        assert c.size() == 0
        assert c.get("x") is None

    def test_size(self):
        c = FIFOCache(5)
        for i in range(3):
            c.put(str(i), i)
        assert c.size() == 3

    def test_contains(self):
        c = FIFOCache(3)
        c.put("hello", "world")
        assert c.contains("hello") is True
        assert c.contains("nope")  is False



class TestCacheManager:
    def _manager(self, policy="LRU", capacity=4) -> CacheManager:
        return CacheManager(capacity=capacity, policy=Policy[policy])

    def test_default_policy_is_lru(self):
        m = CacheManager()
        assert m.active_policy == Policy.LRU

    @pytest.mark.asyncio
    async def test_put_and_get_l1_hit(self):
        m = self._manager()
        await m.put("foo", b"bar")
        value, tier = await m.get("foo")
        assert value == b"bar"
        from aegiscache.cache.manager import Tier
        assert tier == Tier.L1_MEMORY

    @pytest.mark.asyncio
    async def test_get_miss_goes_to_db(self):
        m = CacheManager(capacity=4, policy=Policy.LRU, db_latency_s=0.001)
        value, tier = await m.get("no-such-key")
        from aegiscache.cache.manager import Tier
        assert value is None
        assert tier == Tier.DB_BACKEND

    @pytest.mark.asyncio
    async def test_delete(self):
        m = self._manager()
        await m.put("x", b"1")
        deleted = await m.delete("x")
        assert deleted is True
        value, _ = await m.get("x")
        assert value is None

    @pytest.mark.asyncio
    async def test_swap_policy_migrates_keys(self):
        m = CacheManager(capacity=10, policy=Policy.LRU)
        await m.put("k1", b"v1")
        await m.put("k2", b"v2")
        await m.put("k3", b"v3")

        result = await m.swap_policy(Policy.FIFO, new_capacity=10)
        assert result["new_policy"]    == Policy.FIFO
        assert result["migrated_keys"] == 3
        assert m.active_policy         == Policy.FIFO

        v1, _ = await m.get("k1")
        assert v1 == b"v1"

    @pytest.mark.asyncio
    async def test_swap_policy_lru_to_lfu(self):
        m = CacheManager(capacity=10, policy=Policy.LRU)
        for i in range(5):
            await m.put(f"key{i}", f"val{i}".encode())

        await m.swap_policy(Policy.LFU)
        assert m.active_policy == Policy.LFU
        v, _ = await m.get("key0")
        assert v == b"val0"

    @pytest.mark.asyncio
    async def test_observer_receives_events(self):
        m = self._manager()
        received: list[EventKind] = []

        async def observer(event):
            received.append(event.kind)

        m.subscribe(observer)
        await m.put("obs", b"data")
        await m.get("obs") 
        await m.get("nope")  

        await asyncio.sleep(0.05)

        assert EventKind.HIT  in received
        assert EventKind.MISS in received

    @pytest.mark.asyncio
    async def test_policy_change_event_broadcast(self):
        m = self._manager()
        received_kinds: list[EventKind] = []

        async def observer(event):
            received_kinds.append(event.kind)

        m.subscribe(observer)
        await m.swap_policy(Policy.FIFO)
        await asyncio.sleep(0.01)

        assert EventKind.POLICY_CHANGE in received_kinds

    @pytest.mark.asyncio
    async def test_stats_update_after_operations(self):
        m = CacheManager(capacity=4, policy=Policy.LRU, db_latency_s=0.001)
        await m.put("a", b"1")
        await m.get("a")     
        await m.get("miss")   

        s = m.get_stats()
        assert s["l1_hits"]        == 1
        assert s["db_hits"]        == 1
        assert s["total_requests"] == 2

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            LRUCache(0)
        with pytest.raises(ValueError):
            LFUCache(-1)


class TestEdgeCases:
    def test_lru_get_then_put_same_key(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.get("a")       
        c.put("a", 11)   
        assert c.get("a") == 11
        assert c.size() == 2

    def test_lfu_capacity_one(self):
        c = LFUCache(1)
        c.put("first", 1)
        evicted = c.put("second", 2)
        assert evicted == "first"
        assert c.get("second") == 2

    def test_fifo_capacity_one(self):
        c = FIFOCache(1)
        c.put("a", 1)
        evicted = c.put("b", 2)
        assert evicted == "a"
        assert c.get("b") == 2

    def test_all_strategies_handle_none_value(self):
        """Strategies should store None as a legitimate value."""
        for cls in (LRUCache, LFUCache, FIFOCache):
            c = cls(4)
            c.put("null_val", None)
            assert c.contains("null_val"), f"{cls.__name__} failed contains check for None value"