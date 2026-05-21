
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Optional


# 3 eviction strategies are implemented here: LRU, LFU, and FIFO.
# Abstract Base CLass is defined for the eviction strategy interface, which all concrete strategies must implement.

class EvictionStrategy(ABC):
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Cache capacity must be a positive integer.")  # capacity<=0 is invalid
        self.capacity = capacity
        # Counters exposed to CacheManager for metrics
        self._hits   = 0
        self._misses = 0
        self._evictions = 0

    # Public interface
    # Every cache must implement these methods to be compatible with CacheManager, which relies on this interface for cache operations and metrics collection.      

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Return the cached value or None on a miss."""

    @abstractmethod
    def put(self, key: str, value: Any) -> Optional[str]:
        """
        Insert or update *key*. Returns the evicted key (str) when the cache
        is full and a victim was removed; returns None otherwise.
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove *key* explicitly. Returns True if the key existed."""

    @abstractmethod
    def contains(self, key: str) -> bool:
        """Return True if *key* is present (without touching access metadata)."""

    @abstractmethod
    def size(self) -> int:
        """Return the current number of stored keys."""

    @abstractmethod
    def clear(self) -> None:
        """Evict all keys and reset internal state."""


    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits":      self._hits,
            "misses":    self._misses,
            "evictions": self._evictions,
            "hit_rate":  round(self._hits / total, 4) if total else 0.0,
            "size":      self.size(),
            "capacity":  self.capacity,
            "policy":    self.__class__.__name__,
        }

    def reset_stats(self) -> None:
        self._hits = self._misses = self._evictions = 0



# Doubly Linked List implementation for LRUCache. Each node stores a key-value pair and pointers to the previous and next nodes. The list maintains the order of access, with the head representing the most recently used (MRU) end and the tail representing the least recently used (LRU) end. The LRUCache uses this list to efficiently promote accessed nodes to the MRU position and evict nodes from the LRU position when necessary.

class _DLLNode:

    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: str = "", value: Any = None) -> None:
        self.key   = key
        self.value = value
        self.prev: Optional[_DLLNode] = None
        self.next: Optional[_DLLNode] = None


class _DoublyLinkedList:

    def __init__(self) -> None:
        self.head = _DLLNode()   # Acts as most-recently-used end
        self.tail = _DLLNode()   # Acts as least-recently-used end
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: _DLLNode) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def push_front(self, node: _DLLNode) -> None:  # This is for adding a new node to the front of the list (MRU position)
        node.next       = self.head.next
        node.prev       = self.head
        self.head.next.prev = node
        self.head.next  = node

    def move_to_front(self, node: _DLLNode) -> None: # This is for moving an existing node to the front of the list (MRU position) when it is accessed. It first removes the node from its current position and then pushes it to the front.
        self._remove(node)
        self.push_front(node)

    def pop_tail(self) -> Optional[_DLLNode]:
        lru = self.tail.prev
        if lru is self.head:
            return None
        self._remove(lru)
        return lru

# strategy 1 — LRU  (O(1) get and put with a hash map + doubly linked list)


class LRUCache(EvictionStrategy):

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._map:  dict[str, _DLLNode] = {}
        self._list: _DoublyLinkedList   = _DoublyLinkedList()


    def get(self, key: str) -> Optional[Any]:
        node = self._map.get(key)
        if node is None:
            self._misses += 1
            return None
        self._list.move_to_front(node)
        self._hits += 1
        return node.value

    def put(self, key: str, value: Any) -> Optional[str]:
        evicted_key: Optional[str] = None

        if key in self._map:
            node = self._map[key]
            node.value = value
            self._list.move_to_front(node)
        else:
            if len(self._map) >= self.capacity:
                lru_node = self._list.pop_tail()
                if lru_node:
                    del self._map[lru_node.key]
                    evicted_key = lru_node.key
                    self._evictions += 1
            new_node = _DLLNode(key, value)
            self._list.push_front(new_node)
            self._map[key] = new_node

        return evicted_key

    def delete(self, key: str) -> bool:
        node = self._map.pop(key, None)
        if node is None:
            return False
        self._list._remove(node)
        return True

    def contains(self, key: str) -> bool:
        return key in self._map

    def size(self) -> int:
        return len(self._map)

    def clear(self) -> None:
        self._map.clear()
        self._list = _DoublyLinkedList()


# ── Strategy 2 — LFU  (O(1) get and put with a hash map + frequency buckets)

class _LFUEntry:

    __slots__ = ("key", "value", "freq", "inserted_at")

    def __init__(self, key: str, value: Any, freq: int = 1) -> None:
        self.key         = key
        self.value       = value
        self.freq        = freq
        self.inserted_at = time.monotonic_ns()   # tie-break older entries first


class LFUCache(EvictionStrategy):

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._store:    dict[str, _LFUEntry]            = {}
        self._freq_map: dict[int, dict[str, None]]      = {} # Instead of storing entries directly in the frequency buckets, we store keys with None values to save memory. As we already have the full entry data in the _store dict, we can look up the entry by key when we need to access its frequency or value.
        self._min_freq: int                             = 0

# _freq_map is in a format of {freq: {key: None}}. {1 : {"key1": None, "key2": None}, 2: {"key3": None}}.

    def _increment_freq(self, entry: _LFUEntry) -> None:
        old_freq = entry.freq
        bucket   = self._freq_map[old_freq] # Get the current frequency bucket for the entry's old frequency. 
        del bucket[entry.key] # Delete the entry's key from the old frequency bucket since its frequency will be incremented.

        if not bucket and old_freq == self._min_freq: # If the old frequency bucket is now empty and it was the minimum frequency, we need to update the minimum frequency to the next level. This is because the entry's frequency has been incremented, so the minimum frequency may have changed.
            # For Example if the minimum frequency was 1 and we just incremented an entry from frequency 1 to frequency 2, then we need to check if there are any other entries with frequency 1. If there are none left, we can safely increment the minimum frequency to 2.
            del self._freq_map[old_freq]
            self._min_freq += 1
        elif not bucket:
            del self._freq_map[old_freq]

        entry.freq += 1
        self._freq_map.setdefault(entry.freq, {})[entry.key] = None

    def _evict_lfu(self) -> Optional[str]:
        if self._min_freq not in self._freq_map:
            return None
        bucket = self._freq_map[self._min_freq]
        victim_key = next(iter(bucket)) # Get the oldest key in the minimum frequency bucket.
        del bucket[victim_key]
        if not bucket: # If the bucket is now empty after removing the victim key, we can delete the bucket from the frequency map. We don't need to update the minimum frequency here because it will be updated on the next get/put operation when we increment frequencies.
            del self._freq_map[self._min_freq]
        del self._store[victim_key]
        self._evictions += 1
        return victim_key

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        self._increment_freq(entry)
        self._hits += 1
        return entry.value

    def put(self, key: str, value: Any) -> Optional[str]:
        evicted_key: Optional[str] = None

        if key in self._store:
            entry = self._store[key]
            entry.value = value
            self._increment_freq(entry)
        else:
            if len(self._store) >= self.capacity:
                evicted_key = self._evict_lfu()

            new_entry = _LFUEntry(key, value, freq=1)
            self._store[key] = new_entry
            self._freq_map.setdefault(1, {})[key] = None
            self._min_freq = 1   # freshly inserted entries always have freq=1

        return evicted_key

    def delete(self, key: str) -> bool:
        entry = self._store.pop(key, None)
        if entry is None:
            return False
        bucket = self._freq_map.get(entry.freq, {})
        bucket.pop(key, None)
        if not bucket and entry.freq in self._freq_map:
            del self._freq_map[entry.freq]
        return True

    def contains(self, key: str) -> bool:
        return key in self._store

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
        self._freq_map.clear()
        self._min_freq = 0
# Strategy 3 — FIFO  (O(1) get and put with a hash map + queue)

class FIFOCache(EvictionStrategy):

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._store: dict[str, Any]  = {}
        self._order: deque[str]      = deque()  # left = oldest

    def get(self, key: str) -> Optional[Any]:
        value = self._store.get(key)
        if value is None and key not in self._store:
            self._misses += 1
            return None
        self._hits += 1
        return value

    def put(self, key: str, value: Any) -> Optional[str]:
        evicted_key: Optional[str] = None

        if key in self._store:
            # if the key already exists, we simply update its value without changing its position in the queue. This is because FIFO eviction is based on insertion order, not access order, so updating an existing key should not affect its eviction priority.
            self._store[key] = value
        else:
            if len(self._store) >= self.capacity: # If the cache is at capacity, we need to evict the oldest entry before adding the new one. We do this by popping the leftmost key from the order deque, which represents the oldest entry, and then deleting that key from the store. We also keep track of the evicted key to return it at the end of the method.
                victim = self._order.popleft()
                del self._store[victim]
                evicted_key = victim
                self._evictions += 1
            self._store[key] = value
            self._order.append(key)

        return evicted_key

    def delete(self, key: str) -> bool:
        if key not in self._store:
            return False
        del self._store[key]
        # O(n) removal from deque — acceptable since explicit deletes are rare
        try:
            self._order.remove(key)
        except ValueError:
            pass
        return True

    def contains(self, key: str) -> bool:
        return key in self._store

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
        self._order.clear()