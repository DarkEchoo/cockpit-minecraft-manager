import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
SOURCE=Path(__file__).resolve().parents[1]/"backend/cockpit-minecraft-curseforge-browser"
spec=importlib.util.spec_from_loader('browser_filters',SourceFileLoader('browser_filters',str(SOURCE)))
browser=importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)

class BrowserFiltersAndDetailTests(unittest.TestCase):
 def test_categories_are_filtered_by_section(self):
  records={'data':[{'id':100,'name':'Adventure','classId':4471,'isClass':False,'displayIndex':5},
                   {'id':101,'name':'Tech','classId':4471,'isClass':False,'displayIndex':1},
                   {'id':6,'name':'Mods','classId':6,'isClass':True}]}
  with patch.object(browser,'api',return_value=records) as req:
   result=browser.categories('modpacks')
  self.assertEqual([x['id'] for x in result],[101,100])
  self.assertEqual(req.call_args.args[1]['classId'],4471)
 def test_download_sort_and_loader_send_curseforge_filters(self):
  def endpoint(path,params=None):
   if path=='categories':return {'data':[{'id':100,'name':'Adventure','classId':4471,'isClass':False}]}
   self.assertEqual(path,'mods/search')
   self.assertEqual(params['sortField'],6)
   self.assertEqual(params['categoryId'],100)
   self.assertEqual(params['modLoaderType'],4)
   self.assertEqual(params['gameVersion'],'1.21.1')
   self.assertEqual(params['index'],20)
   return {'data':[{'id':123,'name':'A'}], 'pagination':{'totalCount':60}}
  with patch.object(browser,'api',side_effect=endpoint):
   result=browser.search_page('','modpacks','1.21.1','100','downloads','fabric','20')
  self.assertEqual(result['next_index'],40)
  self.assertEqual(result['total'],60)
 def test_loader_requires_version(self):
  with self.assertRaisesRegex(ValueError,'Minecraft version'):
   browser.search_page('','mods','','','popular','neoforge','0')
 def test_sort_is_validated(self):
  with self.assertRaises(ValueError):
   browser.search_page('','mods','','','DROP TABLE','any','0')
 def test_project_overview_makes_only_one_remote_call(self):
  with patch.object(browser,'api',return_value={'data':{'id':10,'name':'ATM10'}}) as req:
   result=browser.project(10)
  self.assertEqual(result['name'],'ATM10')
  self.assertEqual(req.call_count,1)
 def test_description_is_capped(self):
  with patch.object(browser,'api',return_value={'data':'X'*10000}):
   result=browser.project_description(10)
  self.assertEqual(len(result['description']),4000)
if __name__=='__main__':unittest.main()
