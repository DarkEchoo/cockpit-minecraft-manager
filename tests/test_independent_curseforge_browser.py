import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch
import sys
import unittest

sys.dont_write_bytecode=True
SOURCE=Path(__file__).resolve().parents[1]/"backend/cockpit-minecraft-curseforge-browser"
spec=importlib.util.spec_from_loader("curseforge_browser", SourceFileLoader("curseforge_browser",str(SOURCE)))
browser=importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)

class IndependentBrowserTests(unittest.TestCase):
 def test_versions_filter(self):
  response={'data':[{'approved':True,'versionString':'1.21.1'},{'approved':True,'versionString':'1.20.1'},{'approved':False,'versionString':'9.9'}]}
  with patch.object(browser,'api',return_value=response):
   self.assertEqual(browser.main(['versions']),['1.21.1','1.20.1'])
 def test_fallback_versions_when_minecraft_endpoint_is_empty(self):
  def endpoint(path, params=None):
   if path=='minecraft/version':return {'data':[]}
   if path=='games/432/versions':
    return {'data':[{'type':1,'versions':['1.20.1','Fabric','1.21.1','24w06a','1.21.1']}]}
   raise AssertionError(path)
  with patch.object(browser,'api',side_effect=endpoint):
   self.assertEqual(browser.main(['versions']),['1.21.1','1.20.1'])
 def test_diagnose_only_shows_counts_not_credentials(self):
  def endpoint(path,params=None):
   return {'data':[{'id':1,'name':'Private data not returned'}]}
  with patch.object(browser,'api',side_effect=endpoint),patch.object(browser,'KEY',unittest.mock.MagicMock()):
   result=browser.main(['diagnose'])
  self.assertEqual(result['mod_search']['items'],1)
  self.assertNotIn('Private data',str(result))
 def test_restrict_icon_origin(self):
  self.assertEqual(browser.safe_image('https://example.com/x.png'),'')
  self.assertEqual(browser.safe_image('https://media.forgecdn.net/p.png'),'https://media.forgecdn.net/p.png')
 def test_search_and_categories(self):
  with patch.object(browser,'api',return_value={'data':[{'id':9,'name':'Test','logo':{'thumbnailUrl':'https://media.forgecdn.net/a.png'}}]}) as mocked:
   result=browser.main(['search','Test','mods','1.21.1'])
  self.assertEqual(result[0]['icon'],'https://media.forgecdn.net/a.png')
  self.assertEqual(mocked.call_args.args[1]['classId'],6)
 def test_project_has_description_and_filtered_version_choices(self):
  def responder(endpoint,params=None):
   if endpoint=='mods/12':return {'data':{'id':12,'name':'A Pack'}}
   if endpoint=='mods/12/description':return {'data':'Plain description'}
   if endpoint=='mods/12/files':return {'data':[{'id':43,'fileName':'pack.zip','gameVersions':['Fabric','1.21.1']}]}
   raise AssertionError(endpoint)
  with patch.object(browser,'api',side_effect=responder):
   detail=browser.main(['project','12'])
  self.assertEqual(detail['name'],'A Pack')
  with patch.object(browser,'api',side_effect=responder):
   self.assertEqual(browser.main(['description','12'])['description'],'Plain description')
   self.assertEqual(browser.main(['files','12'])[0]['game_versions'],['Fabric','1.21.1'])
 def test_disallow_remote_html_and_key_exposure(self):
  with self.assertRaises(ValueError):browser.search('test','mods','../etc')
  self.assertNotIn('x-api-key',str(browser.project_summary({'name':'demo','id':1})))
if __name__=='__main__':unittest.main()
