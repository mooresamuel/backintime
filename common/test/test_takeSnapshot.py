# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import snapshots
import mount


class Take(generic.SnapshotsTestCase):
    def setUp(self):
        super().setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(self.include.name)

    def tearDown(self):
        super().tearDown()
        self.include.cleanup()

    def remount(self):
        # dummy method only used in TestTakeSnapshotSSH
        pass

    def getInode(self, sid):
        return os.stat(sid.pathBackup(os.path.join(self.include.name, 'test'))).st_ino

    @patch('time.sleep')  # speed up unittest
    def test_four_snapshots(self, sleep):
        now = datetime.today() - timedelta(minutes = 6)
        sid1 = snapshots.SID(now, self.cfg)

        # Note: 'self.sn' is of type 'Snapshots'
        # First boolean: Snapshot succeeded
        # Second boolean: Error occurred
        self.assertListEqual(
                [True, False],  # Snapshot without error
                self.sn.takeSnapshot(
                    sid=sid1,
                    now=now,
                    include_folders=[
                        (self.include.name, 0),  # '0' means it is a file
                    ]
                )
        )

        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'test')))
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'file with spaces')))
        self.assertExists(self.cfg.anacronSpoolFile())
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertExists(sid1.path(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertNotExists(sid1.path(f))

        # second takeSnapshot which should not create a new snapshot as nothing
        # has changed
        os.remove(self.cfg.anacronSpoolFile())
        now = datetime.today() - timedelta(minutes = 4)
        sid2 = snapshots.SID(now, self.cfg)

        self.assertListEqual([False, False], self.sn.takeSnapshot(sid2, now, [(self.include.name, 0),]))
        self.assertFalse(sid2.exists())
        self.assertExists(self.cfg.anacronSpoolFile())

        # third takeSnapshot
        self.remount()
        with open(os.path.join(self.include.name, 'lalala'), 'wt') as f:
            f.write('asdf')

        now = datetime.today() - timedelta(minutes = 2)
        sid3 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn.takeSnapshot(sid3, now, [(self.include.name, 0),]))
        self.assertTrue(sid3.exists())
        self.assertTrue(sid3.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'lalala')))
        inode1 = self.getInode(sid1)
        inode3 = self.getInode(sid3)
        self.assertEqual(inode1, inode3)

        # fourth takeSnapshot with force create new snapshot even if nothing
        # has changed
        self.cfg.setTakeSnapshotRegardlessOfChanges(True)
        now = datetime.today()
        sid4 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn.takeSnapshot(sid4, now, [(self.include.name, 0),]))
        self.assertTrue(sid4.exists())
        self.assertTrue(sid4.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid4.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'test')))

    @patch('time.sleep') # speed up unittest
    def test_spaces_in_include(self, sleep):
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)
        include = os.path.join(self.include.name, 'test path with spaces')
        generic.create_test_files(include)

        self.assertListEqual([True, False], self.sn.takeSnapshot(sid1, now, [(include, 0),]))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(include, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(include, 'test')))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertExists(sid1.path(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertNotExists(sid1.path(f))

    @patch('time.sleep') # speed up unittest
    def test_exclude(self, sleep):
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)
        self.cfg.setExclude(['bar/baz'])

        self.assertListEqual([True, False], self.sn.takeSnapshot(sid1, now, [(self.include.name, 0),]))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'foo', 'bar')))
        self.assertFalse(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'test')))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertExists(sid1.path(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertNotExists(sid1.path(f))

    @patch('time.sleep') # speed up unittest
    def test_spaces_in_exclude(self, sleep):
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)
        exclude = os.path.join(self.include.name, 'test path with spaces')
        generic.create_test_files(exclude)
        self.cfg.setExclude([exclude])

        self.assertListEqual([True, False], self.sn.takeSnapshot(sid1, now, [(self.include.name, 0),]))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'test')))
        self.assertFalse(sid1.isExistingPathInsideSnapshotFolder(exclude))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertExists(sid1.path(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertNotExists(sid1.path(f))

    @patch('time.sleep') # speed up unittest
    def test_error(self, sleep):
        with generic.mockPermissions(os.path.join(self.include.name, 'test')):
            now = datetime.today()
            sid1 = snapshots.SID(now, self.cfg)

            self.assertListEqual([True, True], self.sn.takeSnapshot(sid1, now, [(self.include.name, 0),]))
            self.assertTrue(sid1.exists())
            self.assertTrue(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
            self.assertFalse(sid1.isExistingPathInsideSnapshotFolder(os.path.join(self.include.name, 'test')))
            for f in ('config',
                      'fileinfo.bz2',
                      'info',
                      'takesnapshot.log.bz2',
                      'failed'):
                self.assertExists(sid1.path(f))
            self.assertNotExists(self.cfg.anacronSpoolFile())

    @patch('time.sleep') # speed up unittest
    def test_error_without_continue(self, sleep):
        with generic.mockPermissions(os.path.join(self.include.name, 'test')):
            self.cfg.setContinueOnErrors(False)
            now = datetime.today()
            sid1 = snapshots.SID(now, self.cfg)

            self.assertListEqual([False, True], self.sn.takeSnapshot(sid1, now, [(self.include.name, 0),]))
            self.assertFalse(sid1.exists())

    @patch('time.sleep') # speed up unittest
    def test_new_exists(self, sleep):
        new_snapshot = snapshots.NewSnapshot(self.cfg)
        new_snapshot.makeDirs()
        with open(new_snapshot.path('leftover'), 'wt') as f:
            f.write('foo')

        now = datetime.today() - timedelta(minutes = 6)
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn.takeSnapshot(sid1, now, [(self.include.name, 0),]))
        self.assertTrue(sid1.exists())
        self.assertNotExists(sid1.path('leftover'))

    @patch('time.sleep') # speed up unittest
    def test_new_exists_continue(self, sleep):
        new_snapshot = snapshots.NewSnapshot(self.cfg)
        new_snapshot.makeDirs()
        with open(new_snapshot.path('leftover'), 'wt') as f:
            f.write('foo')
        new_snapshot.saveToContinue = True

        now = datetime.today() - timedelta(minutes = 6)
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn.takeSnapshot(sid1, now, [(self.include.name, 0),]))
        self.assertTrue(sid1.exists())
        self.assertExists(sid1.path('leftover'))

    @patch('time.sleep')  # speed up unittest
    def test_fail_create_new_snapshot(self, sleep):
        with generic.mockPermissions(self.snapshotPath, 0o500):
            now = datetime.today()
            sid1 = snapshots.SID(now, self.cfg)

            self.assertListEqual([False, True], self.sn.takeSnapshot(sid1, now, [(self.include.name, 0),]))


@unittest.skipIf(
    not generic.LOCAL_SSH,
    'Skip as this test requires a local ssh server, '
    'public and private keys installed')
class TakeSSH(generic.SSHSnapshotTestCase, Take):
    def setUp(self):
        super().setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(self.include.name)

        #mount
        self.cfg.setCurrentHashId(mount.Mount(cfg = self.cfg).mount())

    def tearDown(self):
        #unmount
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        super().tearDown()

        self.include.cleanup()

    def remount(self):
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        mount.Mount(cfg = self.cfg).mount()

    def getInode(self, sid):
        return os.stat(os.path.join(self.snapshotPath, sid.sid, 'backup', self.include.name[1:], 'test')).st_ino
