import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import unittest
from unittest.mock import patch
import sys

sys.dont_write_bytecode=True
SOURCE=Path(__file__).resolve().parents[1]/"backend/cockpit-minecraft-curseforge-browser"
spec=importlib.util.spec_from_loader('curseforge_setup',SourceFileLoader('curseforge_setup',str(SOURCE)))
browser=importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)

class CurseForgeServerPlanTests(unittest.TestCase):
 def plan(self,**changes):
  cfg=dict(project_id='101',file_id='202',name='atm10-test',
           directory='/opt/minecraft/managed/atm10-test',ram_gib='8',
           cpu_cores='2',port='0',repository='',schedule='off',
           interval='1440',restore_export='',eula='true')
  cfg.update(changes)
  with patch.object(browser,'api',return_value={'data':{'id':202,'modId':101,'fileName':'ATM10.zip',
      'gameVersions':['1.21.1','NeoForge'],'serverPackFileId':303}}),patch.object(browser.os,'cpu_count',return_value=8):
   return browser.server_plan(**cfg)
 def test_preview_contains_settings_and_never_enables_creation(self):
  result=self.plan()
  self.assertEqual(result['ram_gib'],8)
  self.assertEqual(result['cpu_cores'],2)
  self.assertEqual(result['server_pack_file_id'],303)
  self.assertFalse(result['create_enabled'])
  self.assertEqual(result['mode'],'review-only')
 def test_path_cannot_target_existing_work(self):
  for location in ('/etc/atm10-test','/opt/minecraft/managed/../atm10-test',
                   '/opt/minecraft/managed/another'):
   with self.subTest(location=location),self.assertRaises(ValueError):
    self.plan(directory=location)
 def test_cpu_limit_bounds(self):
  with self.assertRaises(ValueError):self.plan(cpu_cores='10')
 def test_schedule_needs_existing_restic_path(self):
  with self.assertRaises(ValueError):self.plan(schedule='daily')
 def test_mismatched_project_and_file_are_refused(self):
  with self.assertRaises(ValueError):self.plan(file_id='203')
 def test_preview_does_not_require_minecraft_eula_agreement(self):
  result=self.plan(eula='false')
  self.assertFalse(result['eula_accepted'])
if __name__=='__main__':unittest.main()
