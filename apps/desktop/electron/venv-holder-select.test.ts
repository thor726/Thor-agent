import assert from 'node:assert/strict'

import { test } from 'vitest'

import { hasWindowsPathPrefix, isExternalVenvHolder, isThorOwnedVenvDaemon } from './venv-holder-select'

const SCRIPTS = 'C:\\Thor\\venv\\Scripts'

test('matches the hindsight daemon shim (exe under venv Scripts + hindsight cmdline)', () => {
  assert.equal(
    isThorOwnedVenvDaemon(
      'C:\\Thor\\venv\\Scripts\\pythonw.exe',
      'C:\\Thor\\venv\\Scripts\\pythonw.exe -m hindsight_api.main --daemon --idle-timeout 300 --port 9177',
      SCRIPTS
    ),
    true
  )
})

test('Windows path prefix match is ordinal case-insensitive', () => {
  assert.equal(
    isThorOwnedVenvDaemon(
      'c:\\thor\\venv\\scripts\\python.exe',
      'python.exe -m hindsight_api.main --daemon',
      'C:\\Thor\\venv\\Scripts'
    ),
    true
  )
})

test('excludes external venv holders that are not the hindsight daemon', () => {
  // a user terminal running the thor CLI from the venv — must NOT be killed
  assert.equal(isThorOwnedVenvDaemon('C:\\Thor\\venv\\Scripts\\thor.exe', 'thor chat -q "hi"', SCRIPTS), false)
  // an unrelated python script using the venv interpreter
  assert.equal(
    isThorOwnedVenvDaemon('C:\\Thor\\venv\\Scripts\\python.exe', 'python C:\\tools\\import.py', SCRIPTS),
    false
  )
})

test('excludes exes outside the venv even when the cmdline mentions hindsight', () => {
  assert.equal(
    isThorOwnedVenvDaemon('C:\\Other\\pythonw.exe', 'pythonw -m hindsight_api.main --daemon', SCRIPTS),
    false
  )
})

test('prefix boundary: sibling dirs (ScriptsX) do not match', () => {
  assert.equal(hasWindowsPathPrefix('C:\\Thor\\venv\\ScriptsX\\python.exe', SCRIPTS), false)
  assert.equal(hasWindowsPathPrefix('C:\\Thor\\venv\\Scripts\\python.exe', SCRIPTS), true)
})

test('null/undefined fields never match', () => {
  assert.equal(isThorOwnedVenvDaemon(null, 'x', SCRIPTS), false)
  assert.equal(isThorOwnedVenvDaemon('C:\\Thor\\venv\\Scripts\\pythonw.exe', null, SCRIPTS), false)
  assert.equal(isThorOwnedVenvDaemon(undefined, undefined, SCRIPTS), false)
})

// --- isExternalVenvHolder (#62311) ------------------------------------------

test('matches the autostart gateway shim (thor.exe under venv Scripts)', () => {
  assert.equal(
    isExternalVenvHolder(
      'C:\\Thor\\venv\\Scripts\\thor.exe',
      '"C:\\Thor\\venv\\Scripts\\thor.exe" gateway run --external-supervisor',
      SCRIPTS
    ),
    true
  )
})

test('matches the dashboard scheduled task (python -m thor_cli / -m thor)', () => {
  assert.equal(
    isExternalVenvHolder(
      'C:\\Thor\\venv\\Scripts\\python.exe',
      '"C:\\Thor\\venv\\Scripts\\python.exe" -m thor_cli.main dashboard',
      SCRIPTS
    ),
    true
  )
  assert.equal(
    isExternalVenvHolder('C:\\Thor\\venv\\Scripts\\pythonw.exe', 'pythonw.exe -m thor serve', SCRIPTS),
    true
  )
})

test('never matches an unrelated process that merely borrows the venv interpreter', () => {
  // a user's own script running on the venv python — NOT Thor, must NOT be killed
  assert.equal(
    isExternalVenvHolder('C:\\Thor\\venv\\Scripts\\python.exe', 'python C:\\tools\\import.py', SCRIPTS),
    false
  )
  // hindsight daemon is selected by isThorOwnedVenvDaemon, not here
  assert.equal(
    isExternalVenvHolder('C:\\Thor\\venv\\Scripts\\pythonw.exe', 'pythonw -m hindsight_api.main --daemon', SCRIPTS),
    false
  )
})

test('never matches a process outside the venv, even with thor in the cmdline', () => {
  // an editor / shell whose command line mentions the install root (#62445 regression guard)
  assert.equal(
    isExternalVenvHolder('C:\\Windows\\System32\\cmd.exe', 'cmd /c cd C:\\Thor\\venv\\Scripts && dir', SCRIPTS),
    false
  )
  assert.equal(isExternalVenvHolder('C:\\Other\\thor.exe', 'thor gateway run', SCRIPTS), false)
})

test('sibling-dir and boundary safety for the external selector', () => {
  assert.equal(isExternalVenvHolder('C:\\Thor\\venv\\ScriptsX\\thor.exe', 'thor gateway run', SCRIPTS), false)
  assert.equal(isExternalVenvHolder(null, 'thor gateway run', SCRIPTS), false)
  assert.equal(isExternalVenvHolder('C:\\Thor\\venv\\Scripts\\thor.exe', null, SCRIPTS), false)
})
