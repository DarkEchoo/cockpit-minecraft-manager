import importlib.util
from pathlib import Path
from unittest.mock import patch
import sys
import unittest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 obj=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(obj)
 return obj
policy=load(ROOT/"tools/patch-live-curseforge-manifest.py","policy")
from importlib.machinery import SourceFileLoader
spec=importlib.util.spec_from_loader("browser_ranking",SourceFileLoader("browser_ranking",str(ROOT/"backend/cockpit-minecraft-curseforge-browser")))
browser=importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)

class SearchAndIconTests(unittest.TestCase):
 def test_search_prioritizes_title_match(self):
  response={'data':[{'id':1,'name':'Some random pack','downloadCount':1000000},
   {'id':2,'name':'All the Mods 10 - ATM10','downloadCount':2000},
   {'id':3,'name':'All the Mods 9','downloadCount':10000}]}
  with patch.object(browser,'api',return_value=response) as req:
   results=browser.search('All the Mods','modpacks','')
  self.assertEqual({results[0]['name'],results[1]['name']}, {'All the Mods 10 - ATM10','All the Mods 9'})
  self.assertEqual(results[-1]['name'],'Some random pack')
  self.assertEqual(req.call_args.args[1]['sortField'],13)
 def test_icon_csp_preserves_other_manifest_entries(self):
  source='{"version":1,"tools":{"minecraft":{"path":"index.html"}}}'
  result=policy.patch_manifest(source)
  import json
  data=json.loads(result)
  self.assertEqual(data['tools']['minecraft']['path'],'index.html')
  self.assertIn('img-src',data['content-security-policy'])
  self.assertIn('https://media.forgecdn.net',data['content-security-policy'])
  self.assertNotIn('https:;',data['content-security-policy'])
 def test_custom_csp_other_directives_are_preserved(self):
  import json
  source='{"content-security-policy":"script-src \'self\'; style-src \'self\';"}'
  result=json.loads(policy.patch_manifest(source))
  self.assertIn("script-src 'self'",result['content-security-policy'])
  self.assertIn("style-src 'self'",result['content-security-policy'])
 def test_custom_img_src_rejected(self):
  with self.assertRaises(ValueError):
   policy.patch_manifest('{"content-security-policy":"img-src \'self\'"}')
if __name__=='__main__':unittest.main()
