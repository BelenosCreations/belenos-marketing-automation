"""Attachment schema preview never exports bytes or implies validated media."""
import sqlite3
import unittest

from content_attachments import AttachmentRegistry
from neon_media_schema import (
    MEDIA_TABLE_NAMES,media_ddl_preview,inspect_media_sqlite)


class MediaSchemaPreviewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.store=AttachmentRegistry(self.db)
    def tearDown(self):
        self.db.close()

    def test_schema_matches_source_and_exposes_only_counts(self):
        self.assertEqual(MEDIA_TABLE_NAMES,("content_attachments",))
        ddl=media_ddl_preview()
        self.assertEqual(len(ddl),3)
        self.assertIn("UNIQUE INDEX content_requests_tenant_request_key",ddl[0])
        self.assertIn("FOREIGN KEY(tenant_id,request_id)",ddl[1])
        self.assertIn("CHECK(status IN",ddl[1])
        before=inspect_media_sqlite(self.db)
        self.assertEqual(before["table_count"],1)
        self.assertEqual(before["columns"],9)
        self.assertEqual(before["rows"],0)
        token="private/storage/path/do-not-expose"
        aid=self.store.register_pending(
            tenant_id="shop-secret",request_id="a"*32,item="image",
            media_type="image/png",sha256="b"*64,storage_key=token,now=100)
        after=inspect_media_sqlite(self.db)
        self.assertEqual(after["rows"],1)
        for secret in (token,"shop-secret",aid,"b"*64):
            self.assertNotIn(secret,str(after))
        for flag in ("media_bytes_read","storage_keys_exported",
                     "customer_records_exported","real_scanning_enabled",
                     "media_verified_by_preview","production_ready",
                     "publishing_enabled"):
            self.assertFalse(after[flag])

    def test_missing_or_drifted_registry_fails_closed(self):
        missing=sqlite3.connect(":memory:")
        try:
            with self.assertRaises(ValueError):
                inspect_media_sqlite(missing)
        finally:
            missing.close()
        self.db.execute("ALTER TABLE content_attachments ADD COLUMN stray TEXT")
        with self.assertRaises(ValueError):
            inspect_media_sqlite(self.db)
        with self.assertRaises(TypeError):
            inspect_media_sqlite(None)


if __name__=="__main__":
    unittest.main()
