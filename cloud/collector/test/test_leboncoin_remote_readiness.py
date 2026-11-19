"""Read-only remote Cloudflare schema audit: exact scoping and no mutations."""
import importlib.util
import pathlib
import unittest

SRC=pathlib.Path(__file__).resolve().parents[1]/"tools"/"outlook-remote-readiness.py"
spec=importlib.util.spec_from_file_location("outlook_remote_audit",SRC)
auditmod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditmod)

ACCOUNT="a"*32
DATABASE="123e4567-e89b-12d3-a456-426614174000"

class RemoteAuditTests(unittest.TestCase):
    def mock(self,tables=None,accounts=1,databases=1,triggers=None,account_pages=1,database_pages=1):
        calls=[]
        if tables is None: tables=auditmod.REQUIRED
        if triggers is None: triggers=auditmod.IMMUTABILITY_TRIGGERS
        def request(path,token,*,payload=None):
            calls.append((path,payload))
            if path.startswith("/accounts?"):
                return {"result":[{"id":ACCOUNT} for _ in range(accounts)],"result_info":{"total_pages":account_pages}}
            if path.endswith("/d1/database?per_page=100"):
                return {"result":[{"name":"edge-tcg-history","uuid":DATABASE} for _ in range(databases)],"result_info":{"total_pages":database_pages}}
            if path.endswith("/query"):
                self.assertEqual(payload,{"sql":auditmod.SCHEMA_QUERY})
                return {"result":[{"results":[{"type":"table","name":name} for name in tables]+[{"type":"trigger","name":name} for name in triggers]}]}
            raise AssertionError("Unexpected endpoint")
        return request,calls
    def test_missing_token_is_not_checked(self):
        self.assertEqual(auditmod.audit("")["status"],"NOT_CHECKED")
    def test_schema_is_reported_without_sensitive_records(self):
        req,calls=self.mock()
        result=auditmod.audit("secret-test-token",req)
        self.assertEqual(result["status"],"SCHEMA_OBJECTS_PRESENT_UNVERIFIED")
        self.assertFalse(result["remote_migrations_verified"])
        self.assertTrue(result["schema_objects_present"])
        self.assertFalse(result["production_collection_active"])
        self.assertNotIn("secret-test-token",str(result))
        self.assertEqual(len(calls),3)
        self.assertEqual(calls[0][0],"/accounts?per_page=100")
        self.assertTrue(all(sql is None for _,sql in calls[:2]))
    def test_missing_tables_are_reported_by_name_only(self):
        req,_=self.mock(tables=("lbc_alert_messages",))
        result=auditmod.audit("token",req)
        self.assertEqual(result["status"],"SCHEMA_INCOMPLETE")
        self.assertEqual(result["found_table_count"],1)
        self.assertFalse(result["remote_migrations_verified"])
        self.assertIn("lbc_sync_lease",result["missing_tables"])
    def test_missing_immutability_triggers_are_fail_closed(self):
        req,_=self.mock(triggers=())
        result=auditmod.audit("token",req)
        self.assertEqual(result["status"],"SCHEMA_INCOMPLETE")
        self.assertIn("lbc_alert_messages_no_delete",result["missing_immutability_triggers"])
        self.assertFalse(result["remote_migrations_verified"])
    def test_uninspected_pagination_fails_closed(self):
        req,_=self.mock(account_pages=2)
        with self.assertRaisesRegex(auditmod.AuditError,"ambiguous_cloudflare_account"):
            auditmod.audit("token",req)
        req,_=self.mock(database_pages=2)
        with self.assertRaisesRegex(auditmod.AuditError,"d1_listing_pagination_unchecked"):
            auditmod.audit("token",req)
    def test_missing_database_is_not_provisioned(self):
        req,calls=self.mock(databases=0)
        result=auditmod.audit("token",req)
        self.assertEqual(result["status"],"UNAVAILABLE")
        self.assertEqual(len(calls),2)
    def test_multiple_accounts_or_duplicate_database_fail_closed(self):
        req,_=self.mock(accounts=2)
        with self.assertRaisesRegex(auditmod.AuditError,"ambiguous_cloudflare_account"):
            auditmod.audit("token",req)
        req,_=self.mock(databases=2)
        self.assertEqual(auditmod.audit("token",req)["status"],"AMBIGUOUS")

if __name__=="__main__":
    unittest.main()
