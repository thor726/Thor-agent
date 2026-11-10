import { describe, expect, it } from 'vitest'

import { commandLineIsThorRuntime } from './thor-process'

// HX003: process identity comes from a whole argv TOKEN, never an argv substring.
describe('commandLineIsThorRuntime (HX003 token matching)', () => {
  it('matches a real Thor gateway command line', () => {
    expect(commandLineIsThorRuntime('thor\0gateway\0run')).toBe(true)
    expect(commandLineIsThorRuntime('thor gateway run')).toBe(true)
    expect(commandLineIsThorRuntime('thor --profile work gateway run')).toBe(true)
  })

  it('matches a Thor launched by an interpreter (basename of a path token)', () => {
    expect(commandLineIsThorRuntime('/venv/bin/python\0/venv/bin/thor\0gateway\0run')).toBe(true)
    expect(commandLineIsThorRuntime('C:\\Thor\\thor.exe gateway run')).toBe(true)
  })

  // The bug this replaces: a bare `.includes('thor')` matched any of these.
  it('does NOT match an unrelated process whose path merely contains "thor"', () => {
    expect(commandLineIsThorRuntime('vim /home/user/thor-notes.txt')).toBe(false)
    expect(commandLineIsThorRuntime('/opt/thorbrew/bin/tool --run')).toBe(false)
    expect(commandLineIsThorRuntime('node /srv/thor-dashboard/server.js')).toBe(false)
    expect(commandLineIsThorRuntime('cat ~/.thor/config.yaml')).toBe(false)
  })

  // G2 (#150283): the real unmanaged-gateway launch is `python -m thor_cli.main … gateway
  // run`, which the executable-basename-only matcher REJECTED — so findRunningGatewayProfiles
  // missed a live gateway at first launch / profile repair. Mirror the canonical Python matcher
  // (gateway.status.looks_like_gateway_command_line): recognize the module entry point, by argv
  // TOKENS not a substring, carrying the gateway subcommand.
  it('matches a module-launched gateway (python -m thor_cli.main … gateway run)', () => {
    expect(commandLineIsThorRuntime('python\0-m\0thor_cli.main\0-p\0x\0gateway\0run')).toBe(true)
    expect(commandLineIsThorRuntime('python -m thor_cli.main -p x gateway run')).toBe(true)
    expect(commandLineIsThorRuntime('/venv/bin/python /venv/lib/thor_cli/main.py gateway run')).toBe(true)
    expect(commandLineIsThorRuntime('python -m thor_cli.main --profile work gateway run')).toBe(true)
  })

  it('does NOT match a module entry without the gateway subcommand, nor an unrelated thor-tool path', () => {
    // A thor_cli.main invocation that is not a gateway (e.g. `chat`) is not a running gateway.
    expect(commandLineIsThorRuntime('python -m thor_cli.main chat')).toBe(false)
    // HX003: no substring; an unrelated tool whose path contains "thor" is never a runtime.
    expect(commandLineIsThorRuntime('/opt/thor-tool/foo gateway run')).toBe(false)
    // `-p gateway` is a profile value, not a subcommand.
    expect(commandLineIsThorRuntime('python -m thor_cli.main -p gateway chat')).toBe(false)
  })
})
