"""The scripts are in the right format to run on the Pi."""

import glob
import os
import unittest

from support import REPO

TEXT_FILES = (glob.glob(os.path.join(REPO, '*.py')) + glob.glob(os.path.join(REPO, '*.sh'))
              + glob.glob(os.path.join(REPO, 'tests', '*.py'))
              + [os.path.join(REPO, name) for name in ('config.json', 'colorsettings.txt', 'README.md',
                                                      'requirements.in', '.gitignore', '.gitattributes')])


class RepoFilesTest(unittest.TestCase):

    def test_python_files_compile(self):
        for path in glob.glob(os.path.join(REPO, '*.py')):
            with self.subTest(path=os.path.basename(path)):
                with open(path, encoding='utf-8') as fd:
                    compile(fd.read(), path, 'exec')

    def test_linux_line_endings(self):
        for path in TEXT_FILES:
            with self.subTest(path=os.path.relpath(path, REPO)):
                with open(path, 'rb') as fd:
                    self.assertNotIn(b'\r', fd.read())

    def test_python3_first_line(self):
        for name in ('led_interface.py', 'set_config.py', 'led_solid.py'):
            with self.subTest(name=name):
                with open(os.path.join(REPO, name)) as fd:
                    self.assertEqual(fd.readline().strip(), '#!/usr/bin/env python3')

    def test_shell_scripts_have_shebang(self):
        for path in glob.glob(os.path.join(REPO, '*.sh')):
            with self.subTest(path=os.path.basename(path)):
                with open(path) as fd:
                    self.assertTrue(fd.readline().startswith('#!/'))


if __name__ == '__main__':
    unittest.main()
