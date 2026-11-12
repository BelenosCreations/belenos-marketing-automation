import sqlite3
import os
import tempfile
import threading
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

    def test_invalid_server_timestamps_fail_without_writing(self):
        for value in (-1,True,False,100.0,'100',253402300800):
            for operation in (self.throttle.check,self.throttle.failure):
                with self.subTest(value=value,operation=operation.__name__):
                    with self.assertRaises(ValueError):
                        operation(email='owner@example.com',now=value)
        self.assertEqual(self.db.execute(
            'SELECT count(*) FROM bam_login_throttle').fetchone()[0],0)

    def test_stale_failure_cannot_rewind_window(self):
        self.throttle.failure(email='owner@example.com',now=100)
        self.throttle.failure(email='owner@example.com',now=161)
        self.throttle.failure(email='owner@example.com',now=105)
        self.assertEqual(self.db.execute(
            'SELECT window_start,failures FROM bam_login_throttle'
        ).fetchone(),(161,2))
        self.throttle.failure(email='owner@example.com',now=220)
        self.assertEqual(self.db.execute(
            'SELECT window_start,failures FROM bam_login_throttle'
        ).fetchone(),(161,3))
        self.throttle.failure(email='owner@example.com',now=221)
        self.assertEqual(self.db.execute(
            'SELECT window_start,failures FROM bam_login_throttle'
        ).fetchone(),(221,1))

    def test_atomic_failure_counts_across_independent_clients(self):
        with tempfile.TemporaryDirectory(prefix='bam-throttle-test-') as directory:
            filename=os.path.join(directory,'auth.sqlite3')
            first=sqlite3.connect(filename,timeout=20,check_same_thread=False)
            second=sqlite3.connect(filename,timeout=20,check_same_thread=False)
            try:
                a=LoginThrottle(first,max_failures=3,window_seconds=60)
                b=LoginThrottle(second,max_failures=3,window_seconds=60)
                ready=threading.Barrier(2)
                errors=[]
                def writer(throttle):
                    try:
                        ready.wait(timeout=10)
                        for _ in range(10):
                            throttle.failure(email='SHARED@example.com',now=100)
                    except Exception as exc:
                        errors.append(exc)
                ta=threading.Thread(target=writer,args=(a,))
                tb=threading.Thread(target=writer,args=(b,))
                ta.start()
                tb.start()
                ta.join(timeout=20)
                tb.join(timeout=20)
                self.assertFalse(ta.is_alive() or tb.is_alive())
                self.assertEqual(errors,[])
                count=first.execute('SELECT failures FROM bam_login_throttle '
                    'WHERE identity_hash=?',
                    (a._key('shared@example.com'),)).fetchone()[0]
                self.assertEqual(count,20)
                with self.assertRaises(PermissionError):
                    b.check(email='shared@example.com',now=101)
                b.check(email='shared@example.com',now=160)
                a.failure(email='shared@example.com',now=160)
                self.assertEqual(second.execute(
                    'SELECT window_start,failures FROM bam_login_throttle'
                ).fetchone(),(160,1))
                b.success(email='shared@example.com')
                a.check(email='shared@example.com',now=161)
            finally:
                first.close()
                second.close()

    def test_no_plaintext_email_in_storage(self):
        self.throttle.failure(email='owner@example.com',now=100)
        key=self.db.execute('SELECT identity_hash FROM bam_login_throttle').fetchone()[0]
        self.assertNotIn('owner',key)
        self.assertEqual(len(key),64)

if __name__=='__main__':unittest.main()
