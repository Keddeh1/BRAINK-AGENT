import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('package',Path(__file__).resolve().parents[1]/'scripts/package.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
class PackageTests(unittest.TestCase):
    def test_sensitive_names_rejected(self):
        for name in ['.env','.env.production','web/.env','docs/.env.local','web/secret.key','evidence/local/run.json','secrets/password.json','docs/.ssh/id_rsa','web/../secrets.json']:
            with self.subTest(name=name),self.assertRaises(ValueError):package.validate_name(name)
    def test_reviewed_source_names_admitted(self):
        for name in ['README.md','.gitignore','web/app.js','braink_agent/manager.py','evidence/independent-review.md']:
            package.validate_name(name)
if __name__=='__main__':unittest.main()
