from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"backend/minecraft-manual-backup"

class ManualBackupSafetyTests(unittest.TestCase):
    def test_requires_explicit_host_configuration(self):
        text=SCRIPT.read_text()
        for name in ("MC_BACKUP_MOUNT","MC_BACKUP_UUID","MC_BACKUP_REPO",
                     "MC_BACKUP_PASSWORD_FILE","MC_BACKUP_SOURCE",
                     "MC_BACKUP_SERVICE","MC_BACKUP_ALLOW_STOP"):
            self.assertIn(name,text)
        self.assertNotIn("/mnt/toshiba",text)
        self.assertNotIn("1A30E8D030E8B443",text)
        self.assertNotIn("/opt/minecraft/server-26.2",text)
    def test_missing_config_fails_without_changes(self):
        process=subprocess.run(["bash",str(SCRIPT)],capture_output=True,text=True,
                               env={"PATH":"/usr/bin:/bin","MC_MANUAL_BACKUP_CONFIG":"/no-such-conf"},
                               timeout=5)
        self.assertEqual(process.returncode,2)
        self.assertIn("Missing safe backup configuration",process.stderr)
    def test_syntax(self):
        subprocess.run(["bash","-n",str(SCRIPT)],check=True)

if __name__=="__main__": unittest.main()
