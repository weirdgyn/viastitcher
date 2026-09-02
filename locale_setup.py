from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
import os
import subprocess

class build_py(_build_py):
    def run(self):
        _build_py.run(self)
        # Compile .mo files during build
        for lang in ['en', 'it']:
            po_file = f'viastitcher/locale/{lang}/LC_MESSAGES/viastitcher.po'
            mo_file = f'viastitcher/locale/{lang}/LC_MESSAGES/viastitcher.mo'
            if os.path.exists(po_file):
                subprocess.run(['msgfmt', '-o', mo_file, po_file])

setup(
    name='viastitcher',
    version='0.3.1',
    packages=['viastitcher'],
    package_data={
        'viastitcher': [
            'locale/en/LC_MESSAGES/*.mo',
            'locale/it/LC_MESSAGES/*.mo',
        ]
    },
    cmdclass={'build_py': build_py},
)
