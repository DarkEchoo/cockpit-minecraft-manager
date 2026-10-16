import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE=Path(__file__).resolve().parents[1]/"tools/production-transaction.py"
spec=importlib.util.spec_from_file_location("production_transaction",FILE)
tx=importlib.util.module_from_spec(spec)
spec.loader.exec_module(tx)

class ProductionTransactionFixtures(unittest.TestCase):
    def setup(self,root):
        repo=root/"release"
        for source,_ in tx.PARTS:
            (repo/source).mkdir(parents=True,exist_ok=True)
        (repo/"cockpit/minecraft-manager/manifest.json").write_text('{"menu":{}}')
        (repo/"cockpit/minecraft-manager/app.js").write_text("new")
        (repo/"backend/cockpit-minecraft-helper").write_text("#!/usr/bin/env python3\n")
        (repo/"addons/backup-manager/helpers/cockpit-mc-schedule").write_text("new schedule")
        old=root/"usr/local/share/cockpit/minecraft-manager"
        old.mkdir(parents=True)
        (old/"app.js").write_text("old")
        return repo,old
    def test_apply_and_explicit_rollback(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root=Path(tmp)
            repo,old=self.setup(root)
            result=tx.apply(repo,root)
            self.assertGreater(result["applied"],0)
            self.assertEqual((old/"app.js").read_text(),"new")
            tx.recover(root)
            self.assertEqual((old/"app.js").read_text(),"old")
            self.assertFalse((root/"usr/local/libexec/cockpit-minecraft-helper").exists())
    def test_finalization_retains_new_files(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root=Path(tmp);repo,old=self.setup(root)
            tx.apply(repo,root)
            tx.finalize(root)
            self.assertEqual((old/"app.js").read_text(),"new")
            self.assertFalse((root/tx.TRANSACTION).exists())
    def test_symlink_target_refused(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root=Path(tmp);repo,old=self.setup(root)
            (old/"manifest.json").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError,"Symlink"):
                tx.inventory(repo,root)
            self.assertFalse((root/tx.TRANSACTION).exists())
    def test_partial_file_copy_can_be_recovered(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root=Path(tmp);repo,old=self.setup(root)
            original=tx.shutil.copyfile
            fired=[False]
            def interrupted(source,destination,*args,**kwargs):
                if ".mc-install-" in str(destination) and not fired[0]:
                    fired[0]=True
                    Path(destination).write_text("half written")
                    raise OSError("disk interruption")
                return original(source,destination,*args,**kwargs)
            with patch.object(tx.shutil,"copyfile",side_effect=interrupted):
                with self.assertRaisesRegex(OSError,"disk interruption"):
                    tx.apply(repo,root)
            tx.recover(root)
            self.assertEqual((old/"app.js").read_text(),"old")
            self.assertFalse(list(root.rglob(".mc-install-*")))
    def test_preserves_existing_host_specific_proxy(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root=Path(tmp);repo,_=self.setup(root)
            (repo/"backend/minecraft-default-proxy").write_text("generic version")
            actual=root/"usr/local/libexec/minecraft-default-proxy"
            actual.parent.mkdir(parents=True)
            actual.write_text("host custom version")
            self.assertFalse(any(r["path"].endswith("/minecraft-default-proxy") for r in tx.inventory(repo,root)))
            tx.apply(repo,root)
            self.assertEqual(actual.read_text(),"host custom version")
    def test_existing_console_feature_files_preserved(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root=Path(tmp);repo,frontend=self.setup(root)
            (repo/"backend/cockpit-minecraft-modpacks").write_text("packaged modpack backend")
            (repo/"backend/cockpit-minecraft-records").write_text("packaged records")
            (repo/"backend/cockpit-minecraft-join-control").write_text("packaged control")
            (frontend/"app.js").write_text("live custom frontend")
            helpers=root/"usr/local/libexec"
            helpers.mkdir(parents=True,exist_ok=True)
            for name in ("cockpit-minecraft-helper","cockpit-minecraft-modpacks","cockpit-minecraft-records","cockpit-minecraft-join-control"):
                (helpers/name).write_text("live-"+name)
            records=tx.inventory(repo,root)
            paths={r["path"] for r in records}
            for name in ("cockpit-minecraft-helper","cockpit-minecraft-modpacks","cockpit-minecraft-records","cockpit-minecraft-join-control"):
                self.assertNotIn("usr/local/libexec/"+name,paths)
            self.assertNotIn("usr/local/share/cockpit/minecraft-manager/app.js",paths)
            tx.apply(repo,root)
            self.assertEqual((frontend/"app.js").read_text(),"live custom frontend")
            self.assertEqual((helpers/"cockpit-minecraft-modpacks").read_text(),"live-cockpit-minecraft-modpacks")
    def test_outstanding_install_refused(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root=Path(tmp);repo,_=self.setup(root)
            tx.apply(repo,root)
            with self.assertRaisesRegex(ValueError,"Outstanding"):
                tx.apply(repo,root)
if __name__=="__main__":
    unittest.main()
