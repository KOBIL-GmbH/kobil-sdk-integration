"""Build a portable source-installer ZIP, never a user's generated installation."""
import hashlib
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent.parent
FILES=['claude-install/install.py','claude-install/bridge.py','claude-install/README.md',
       'claude-install/Install Claude.command','claude-install/package.py',
       'claude-install/tests/test_install.py','xcode-plugin/install.py','docs/backend.md','docs/credentials.md']
def main():
 out=ROOT/'dist';out.mkdir(exist_ok=True)
 path=out/'kobil-sdk-claude-installer-0.1.0.zip'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for name in FILES:z.write(ROOT/name,'kobil-sdk-claude-installer/'+name)
 path.with_suffix('.zip.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n')
 print(path)
if __name__=='__main__':main()
