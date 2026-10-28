import unittest
from handoff_diff import compare
class Tests(unittest.TestCase):
    def test_changed_and_missing(self):
        old=[{"id":"a","updated_at":"1"},{"id":"b","updated_at":"1"}]
        new=[{"id":"a","updated_at":"2"},{"id":"c","updated_at":"1"}]
        result=compare(old,new)
        self.assertEqual([x["id"] for x in result["changed"]],["a"])
        self.assertEqual([x["id"] for x in result["added"]],["c"])
        self.assertEqual([x["id"] for x in result["missing_from_snapshot"]],["b"])
    def test_unchanged(self):
        self.assertEqual(compare([{"id":"a"}],[{"id":"a"}])["unchanged_count"],1)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): compare([],[{"id":"a"},{"id":"a"}])
    def test_hash_change(self):
        self.assertEqual(len(compare([{"id":"a","content_sha256":"x"}],[{"id":"a","content_sha256":"y"}])["changed"]),1)
    def test_bad_schema(self):
        with self.assertRaises(ValueError):compare({},[])
if __name__=="__main__":unittest.main()
