"""Package public website assets only; exclude collector and workflow files."""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
site = root / '_site'
if site.exists():
    shutil.rmtree(site)
site.mkdir()
for pattern in ('*.html', '*.css', '*.js', 'CNAME'):
    for source in root.glob(pattern):
        shutil.copy2(source, site / source.name)
for name in ('assets', 'data'):
    shutil.copytree(root / name, site / name)
(site / '.nojekyll').touch()
print('Packaged website in _site')
