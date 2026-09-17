import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
install=load('install');bridge=load('bridge')

class InstallerTests(unittest.TestCase):
 def test_preserves_configuration_and_is_idempotent(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config.json';p.write_text(json.dumps({'preferences':{'x':1},'mcpServers':{'Other':{'command':'other'}}}))
   server={'command':'python','args':['bridge.py']}
   install.merge_desktop(p,server);first=p.read_bytes();install.merge_desktop(p,server)
   self.assertEqual(p.read_bytes(),first)
   cfg=json.loads(first);self.assertEqual(cfg['preferences'],{'x':1});self.assertIn('Other',cfg['mcpServers'])
   self.assertEqual(len(list(Path(d).glob('*.backup-*'))),1)
   with self.assertRaises(RuntimeError):install.merge_desktop(p,{'command':'different'})
   self.assertEqual(p.read_bytes(),first)
 def test_invalid_config_untouched(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config.json'
   for body in ['{','[]','{"mcpServers": []}']:
    p.write_text(body)
    with self.assertRaises(RuntimeError):install.merge_desktop(p,{})
    self.assertEqual(p.read_text(),body)
 def test_guide_boundaries(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'docs').mkdir();(r/'docs/backend.md').write_text('public guide')
   (r/'secret.md').write_text('private')
   self.assertEqual(bridge.read_guide(r,'docs/backend.md'),'public guide')
   for path in ['docs/../secret.md',str(r/'secret.md'),'docs/missing.md']:
    with self.assertRaises(ValueError):bridge.read_guide(r,path)
   (r/'docs/link.md').symlink_to(r/'secret.md')
   with self.assertRaises(ValueError):bridge.read_guide(r,'docs/link.md')
 def test_generated_paths_and_no_credentials(self):
  files,server=install.generated_files(Path('/a path/release'),Path('/a path/setup'))
  self.assertEqual(server['args'],['/a path/setup/bridge.py','/a path/setup/runtime.json'])
  self.assertEqual(json.loads(files['runtime.json'])['keychain'],None)
  self.assertIn('sdk_guide',files['plugin/skills/kobil-sdk-release/SKILL.md'])
  self.assertEqual(json.loads(files['.claude-plugin/marketplace.json'])['plugins'][0]['source'],'./plugin')

if __name__=='__main__':unittest.main()
