"""Compare KiCad DRC reports for boards created by kicad_integration.py."""
import collections
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(sys.argv[1])
cli = os.environ.get('KICAD_CLI') or shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
for style in (0,1,2,'corridor'):
    reports = []
    for stage in ('before','after'):
        stem = root / ('%s_%s' % (stage,style))
        subprocess.run([cli,'pcb','drc','--refill-zones','--format','json','-o',
                        str(stem.with_suffix('.json')),str(stem.with_suffix('.kicad_pcb'))],check=True)
        reports.append(json.loads(stem.with_suffix('.json').read_text()))
    before,after = reports
    def key(v):
        return v['type'],tuple(sorted(item.get('uuid','') for item in v.get('items',[])))
    new = {key(v) for v in after['violations']} - {key(v) for v in before['violations']}
    print('Style',style,'before:',dict(collections.Counter(v['type'] for v in before['violations'])),
          'after:',dict(collections.Counter(v['type'] for v in after['violations'])), 'new:',new)
    assert not new, 'Additional DRC violations introduced by refill'
    assert len(after['unconnected_items']) <= len(before['unconnected_items']), 'Additional unconnected items'
print('No new DRC violations in any fill style or the narrow-corridor fixture.')
