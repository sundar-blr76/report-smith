
import os
import shutil
import time
import unittest
from reportsmith.utils.cache_manager import get_cache_manager, init_cache_manager

class TestCacheRefactor(unittest.TestCase):
    def setUp(self):
        self.test_cache_dir = "/tmp/reportsmith_test_cache"
        # Re-init cache manager with test config
        self.cm = init_cache_manager(
            enable_redis=False,
            enable_disk=True,
            disk_cache_dir=self.test_cache_dir,
            l1_max_size=10
        )
        self.cm.invalidate()

    def tearDown(self):
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)

    def test_l1_cache(self):
        category = "llm_intent"
        key = "test_key"
        value = {"foo": "bar"}
        
        # Miss
        self.assertIsNone(self.cm.get(category, key))
        
        # Set
        self.cm.set(category, value, key)
        
        # Hit
        retrieved = self.cm.get(category, key)
        self.assertEqual(retrieved, value)
        
        # Stats
        stats = self.cm.get_stats(category)
        print(f"L1 Stats: {stats}")
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.sets, 1)

    def test_l3_disk_persistence(self):
        category = "llm_intent"
        key = "disk_key"
        value = {"disk": "data"}
        
        self.cm.set(category, value, key)
        
        # Clear L1 to force disk read
        self.cm.l1_caches[category].clear()
        
        # Hit from disk
        retrieved = self.cm.get(category, key)
        self.assertEqual(retrieved, value)
        
        # Check stats
        stats = self.cm.get_stats(category)
        print(f"Disk Stats: {stats}")
        # 1 hit (disk)
        self.assertEqual(stats.hits, 1)

if __name__ == '__main__':
    unittest.main()
