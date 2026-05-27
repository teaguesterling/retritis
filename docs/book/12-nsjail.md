# 12. nsjail — Sandboxed Execution

When lackpy runs a generated program, the restricted *grammar* (Chapter 9) bounds what the
program can express; **nsjail** bounds what the running process can *do*. Defense in depth:
a narrow language and a narrow runtime.

## Why two layers

The grammar prevents a program from naming dangerous operations in the first place
(`FORBIDDEN_NAMES`/`FORBIDDEN_NODES`). But generation is probabilistic and grammars have
edges, so execution adds an OS-level boundary: a sandboxed process with restricted
filesystem, network, and resource access. If the language layer ever lets something through,
the sandbox is the backstop.

> **Why belt and suspenders.** A single layer fails the moment it has a gap, and you only
> find the gap in production. A restricted language *and* a sandboxed runtime fail
> independently — the realistic failure (a grammar edge case) is caught by the layer that
> doesn't share its assumptions. This is the same instinct as "one policy, two enforcers,"
> applied to safety rather than correctness.

## How it fits lackpy

lackpy's `RestrictedRunner` executes validated programs inside the sandbox, with the kit's
allowed tools as the only sanctioned capabilities. The policy chain (umwelt + kit) decides
*which* tools; nsjail ensures the process can't step outside that decision at the OS level.

## Operating notes

nsjail is the lowest-trust layer, so it is also the one most worth keeping conservative:
prefer denying by default and granting narrowly. If a generated program needs a capability
it doesn't have, the fix is to widen the *kit/policy* deliberately, not to loosen the
sandbox globally.
