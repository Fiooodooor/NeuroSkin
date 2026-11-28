import json
import tempfile
import unittest
from pathlib import Path
from archive_store import ArchiveError, ArchiveStore

class ArchiveTest(unittest.TestCase):
    def test_archive_list_load_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArchiveStore(Path(tmp))
            run = {'id':'run_123','status':'completed','generation':4,'history':[],
                   'best':{'id':'4-2','family':'crown','genome':{'topology':'arched'},'fitness':72.0},
                   'audit_top3':[{'id':'4-2','family':'crown','genome':{}}],
                   'gallery':[{'id':'4-3','family':'quadrant','genome':{}}]}
            folder = store.path('run_123');folder.mkdir()
            (folder/'results.json').write_text(json.dumps(run))
            self.assertEqual(store.load('run_123')['generation'],4)
            self.assertEqual(store.list_runs()[0]['champion_id'],'4-2')
            self.assertEqual(store.lookup(run,'id','4-2')['family'],'crown')
            self.assertEqual(store.lookup(run,'gallery',0)['id'],'4-3')
            self.assertIsNone(store.lookup(run,'gallery','abc'))
    def test_no_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArchiveStore(Path(tmp))
            for item in ['../secret','/etc','a/b','..', 'x'*100]:
                with self.assertRaises(ArchiveError):store.path(item)
    def test_ignore_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ArchiveStore(Path(tmp));dir=store.path('broken');dir.mkdir()
            (dir/'results.json').write_text('{broken')
            self.assertEqual(store.list_runs(),[])
    def test_archive_cannot_be_modified_by_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ArchiveStore(Path(tmp));dir=store.path('good');dir.mkdir()
            (dir/'results.json').write_text(json.dumps({'id':'good','history':[]}))
            a=store.load('good');a['history'].append(5)
            self.assertEqual(store.load('good')['history'],[])

if __name__=='__main__':unittest.main()
