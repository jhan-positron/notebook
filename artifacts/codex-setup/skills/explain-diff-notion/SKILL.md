---
name: explain-diff-notion
description: Use when the user asks for a rich explanation of a code change, diff, branch, or PR as a Notion page. Writes the page through a Notion MCP server when one is configured; otherwise writes a Notion-ready Markdown file for the user to import.
---

# Explain Diff (Notion)

Please make me a rich, interactive explanation of the specified code change as a Notion page.

## Where the page goes

Codex equivalent of the Claude skill of the same name. Claude writes the page with its Notion MCP tools. Codex only has those tools when a Notion MCP server is listed under `[mcp_servers.*]` in `~/.codex/config.toml`. Check the available tools first:

- A Notion tool is available (for example `notion-create-pages`): create a new page with it and return the URL of the new page. Use callouts and toggle blocks as described below.
- No Notion tool is available: write one Markdown file and tell the user to import it into Notion (Notion: Import, or paste the Markdown into a new page). Put the file outside the code repo under `~/workspace/ai-runs/explanations/`, and start the filename with today's date in `YYYY-MM-DD-` format so the files stay time-sorted and out of version control. For example: `~/workspace/ai-runs/explanations/2026-01-12-explanation-<slug>.md`. Say in the reply that the page was written as a file because no Notion tool is configured.

## Sections

- Background: Explain the existing system relevant to this change. (You should broadly explore surrounding code for this.) We don't know how much the reader already knows, so include a deep background for beginners (note that it can be skipped if the reader is already familiar), and then a more narrow background directly relevant to the change.
- Intuition: Explain the core intuition for the code change. The focus here is to explain the essence, not the full details. Use concrete examples with toy data. Use figures and diagrams liberally.
- Code: Do a high-level walkthrough of the changes to the code. Group/order the changes in an understandable way.
- **Quiz**: Come up with 5 questions that test the reader's knowledge of this PR. This should be medium difficulty, difficult enough that you actually need to understand the substance of the PR to answer them, but not gotchas. The goal is to help the reader make sure that they've actually understood. Each question should have some multiple choice answers with an explanation detailing why an answer is correct or incorrect. Use toggle blocks to represent this. For example:
  ```markdown
  1. Question
     ▶ Option 1
      ❌ Explanation for why it was incorrect
     ▶ Option 2
      ❌ Explanation for why it was incorrect
     ▶ Option 3
      ✅ Explanation for why it was correct
     ▶ Option 4
       ❌ Explanation for why it was incorrect
  2. Question
     ...
  ```
  In the Markdown file, write each option as a `<details><summary>Option N</summary>explanation</details>` block. Notion's Markdown import turns these into toggle blocks, and a browser renders them as collapsible sections.

## Format

- Please write with the clarity and flow of Martin Kleppmann, making it engaging and written in classic style. Transitions between sections should be smooth.
- Some tips on diagrams. Ideally, you should pick a small number of diagram families that can be reused throughout the explanation to explain various cases. Make sure to include example data!
- Use callouts for key concepts or definitions, important edge cases, etc. In the Markdown file, a callout is a blockquote whose first line starts with an emoji marker (for example `> 💡 **Key concept:** ...`).
