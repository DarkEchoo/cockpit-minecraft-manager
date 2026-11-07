import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/"tools/patch-live-curseforge-html.py"
spec=importlib.util.spec_from_file_location("patch_live_browser",PATH)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BASE='''<html><body><div id="custom-other-feature">keep me</div>
<div id="mp-key"></div><input id="mp-query">
<select id="mp-category"></select><button id="mp-search"></button>
<input id="mp-search-version" placeholder="1.21.1">
<div id="mp-results"></div>
<script src="modpacks.js"></script>
<section id="independent-console-widget">custom live content</section></body></html>'''

class LiveBrowserHtmlPatchTests(unittest.TestCase):
 def test_replaces_only_browser_control_elements(self):
  result=mod.patch_html(BASE)
  self.assertIn('id="mp-search-version"',result)
  self.assertIn('<select id="mp-search-version"',result)
  self.assertIn('id="mp-project-detail"',result)
  self.assertIn('<div id="custom-other-feature">keep me</div>',result)
  self.assertIn('<section id="independent-console-widget">custom live content</section>',result)
  self.assertNotIn('placeholder="1.21.1"',result)
 def test_rejects_duplicate_version_input(self):
  with self.assertRaises(ValueError):
   mod.patch_html(BASE.replace('<input id="mp-search-version"', '<input id="mp-search-version"><input id="mp-search-version"'))
 def test_rejects_incompatible_results_area(self):
  with self.assertRaises(ValueError):
   mod.patch_html(BASE.replace('<div id="mp-results"></div>','<div id="mp-results"><p>Unexpected content</p></div>'))
 def test_rejects_partial_prior_upgrade(self):
  with self.assertRaises(ValueError):
   mod.patch_html(BASE+'<div id="mp-project-detail"></div>')
if __name__=="__main__":unittest.main()
