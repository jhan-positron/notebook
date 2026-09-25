Introduce typed tensor access for the existing packed V cache and native row-major K cache as a standalone refactor before #4424.

This follows Ben's [tensor-interface review](https://github.com/positron-ai/tron/pull/4424#pullrequestreview-5270587330) and [API sketch](https://github.com/positron-ai/tron/pull/4424#issuecomment-5765866077) in this repository.

Scope:
- Use the existing expr interface for logical tensor and row operations.
- Combine the address mapping with the concrete view. Keep storage ownership separate.
- Preserve existing layouts, conversions, initialization rules, optimized operations, and cache behavior.
- Type cache and kernel boundaries so callers cannot confuse packed V with native K.
- Extend relevant existing tests and verify they execute in required CI.

PR order:
1. Add the abstraction for existing V and native K on main.
2. Rebase #4424 onto that parent and add its packed-K representation.
3. Keep attention algorithm changes and shared-save coordination in #4424. Ben's [save_k worker-interface comment](https://github.com/positron-ai/tron/pull/4424#discussion_r4065141577) remains a separate concern there.

The detailed implementation handoff will be saved in the local issue-number directory requested by the task.
