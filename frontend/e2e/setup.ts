import {execFileSync} from 'node:child_process'
import {resolve} from 'node:path'
export default function setup(){execFileSync(resolve('../.venv/Scripts/python.exe'),[resolve('../backend/tests/generate_e2e.py')])}
