import sqlite3
import unittest
from login_throttle import LoginThrottle

class LoginThrottleTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.throttle=LoginThrottle(self.db,max_failures=3,window_seconds=60)

    def test_lockout_and_window(self):
        for _ in range(3):
            self.throttle.failure(email='Owner@Example.com',now=100)
        with self.assertRaises(PermissionError):
            self.throttle.check(email='owner@example.com',now=120)
        self.throttle.check(email='owner@example.com',now=160)

    def test_other_identity_unaffected(self):
        for _ in range(3):
            self.throttle.failure(email='one@example.com',now=100)
        self.throttle.check(email='two@example.com',now=101)

    def test_success_clears_failures(self):
        for _ in range(3):
            self.throttle.failure(email='owner@example.com',now=100)
        self.throttle.success(email='owner@example.com')
        self.throttle.check(email='owner@example.com',now=101)

    def test_no_plaintext_email_in_storage(self):
        self.throttle.failure(email='owner@example.com',now=100)
        key=self.db.execute('SELECT identity_hash FROM bam_login_throttle').fetchone()[0]
        self.assertNotIn('owner',key)
        self.assertEqual(len(key),64)

if __name__=='__main__':unittest.main()
