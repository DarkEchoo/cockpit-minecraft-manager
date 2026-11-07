import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch
import sys
import unittest

sys.dont_write_bytecode=True
SOURCE=Path(__file__).resolve().parents[1]/"backend/cockpit-minecraft-modpacks"
spec=importlib.util.spec_from_loader("cf_browser", SourceFileLoader("cf_browser",str(SOURCE)))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CurseForgeBrowserTests(unittest.TestCase):
 def test_rejects_unsafe_artwork_url(self):
  for url in ("javascript:alert(1)","http://media.forgecdn.net/image.png","https://evil.example/i.png","https://media.forgecdn.net.evil.example/i.png"):
   self.assertEqual(mod._project_image(url),"")
  self.assertEqual(mod._project_image("https://media.forgecdn.net/i.png"),"https://media.forgecdn.net/i.png")
 def test_version_options_from_api(self):
  sample={"data":[{"approved":True,"versionString":"1.21.1"},{"approved":False,"versionString":"1.99"},{"approved":True,"versionString":"1.20.1"},{"approved":True,"versionString":"1.21.1"}]}
  with patch.object(mod,"api",return_value=sample):self.assertEqual(mod.minecraft_versions(),["1.21.1","1.20.1"])
 def test_search_returns_image_metadata_without_credentials(self):
  data={"data":[{"id":123,"name":"Example pack","summary":"A description","logo":{"thumbnailUrl":"https://media.forgecdn.net/thumb.jpg"},"authors":[{"name":"Creator"}],"downloadCount":1234}]}
  with patch.object(mod,"api",return_value=data) as req:
   result=mod.query("Example","modpacks","1.21.1")
  self.assertEqual(result[0]["icon"],"https://media.forgecdn.net/thumb.jpg")
  self.assertEqual(result[0]["authors"],["Creator"])
  self.assertEqual(req.call_args.args[0],"mods/search")
 def test_project_description_is_plain_text_and_release_versions_available(self):
  project={"data":{"id":10,"name":"Example","logo":{},"summary":"A pack"}}
  def fake_api(endpoint, params=None):
   if endpoint=="mods/10":return project
   if endpoint=="mods/10/description":return {"data":"Clean description"}
   raise AssertionError(endpoint)
  files=[{"id":20,"name":"Example 1.21.1","game_versions":["1.21.1","Fabric"],"release_type":1}]
  with patch.object(mod,"api",side_effect=fake_api),patch.object(mod,"cf_files",return_value=files):
   result=mod.project_details("10")
  self.assertEqual(result["description"],"Clean description")
  self.assertEqual(result["supported_versions"],["1.21.1"])
 def test_invalid_search_version_is_rejected(self):
  with self.assertRaises(ValueError):mod.query("abc","mods","../../bad")
if __name__=="__main__":unittest.main()
