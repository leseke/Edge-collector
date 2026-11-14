"""AI-002C.1 : qualification conservative, tests sans reseau."""
import copy
import unittest
from tests.test_ai002c import Base, NOW, item
from intelligence.evidence import qualify, build_corpus, validate_item

class ScopeQualificationTests(Base):
    def test_unverified_1999_2022_remains_unresolved_not_proven(self):
        a = item(position="2022", scope={"language":"zh-Hans", "definition":"official_launch"})
        b = item(position="1999", origin={"url":"https://other.example.org/page", "method":"search_snippet"},
                 content={"text":"The first Simplified Chinese Pokemon cards were introduced in 1999"})
        self.imp([a,b])
        q = qualify(self.store.items(), NOW)
        self.assertFalse([x for x in q["contradictions"] if x["type"]=="assertion"])
        self.assertEqual(q["scope_reviews"][0]["verdict"], "ambiguous_scope")

    def test_known_scope_difference_is_not_contradiction(self):
        a = item(position="1999", scope={"language":"zh-Hant", "definition":"first_appearance"})
        b = item(position="2022", origin={"url":"https://other.example.org/page"},
                 scope={"language":"zh-Hans", "definition":"official_launch"},
                 content={"text":"2022 simplified launch"})
        self.imp([a,b]); q=qualify(self.store.items(), NOW)
        self.assertFalse(q["contradictions"])
        self.assertEqual(q["scope_reviews"][0]["verdict"],"different_scope")

    def test_genuine_same_scope_direct_disagreement(self):
        full={"territory":"CN", "language":"zh-Hans", "product_line":"TCG",
              "edition":"initial", "definition":"official_launch", "period":"first-release"}
        a=item(position="2022",scope=full)
        b=item(position="2023",scope=full,origin={"url":"https://other.example.org/page"},
               content={"text":"Direct page reports launch 2023"})
        self.imp([a,b]); q=qualify(self.store.items(),NOW)
        self.assertEqual(q["contradictions"][0]["verdict"],"same_scope")

    def test_search_excerpt_never_strong(self):
        a=item(origin={"method":"search_snippet"})
        self.imp([a]); q=qualify(self.store.items(),NOW)
        self.assertEqual(q["provenance_reviews"][0]["collection_level"],"search_excerpt_unconfirmed")
        self.assertFalse(q["provenance_reviews"][0]["strong_evidence"])

    def test_invalid_scope_rejected(self):
        self.assertTrue(any("scope" in x for x in validate_item(item(scope={"new_authority":"YES"}))))

    def test_legacy_items_and_financial_policy_unchanged(self):
        self.imp([item()]); q=qualify(self.store.items(), NOW)
        self.assertIn("mirrors",q)
        self.assertNotIn("policy_decision",q)

if __name__=='__main__': unittest.main()
