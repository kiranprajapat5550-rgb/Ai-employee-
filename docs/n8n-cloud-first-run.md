# n8n Cloud: safe first-run checklist

This checklist is designed for the hosted n8n Cloud workspace. It does not require connecting external accounts or adding API keys.

## Safe test workflow
1. In n8n Cloud, create a workflow named **AI Employee System - Safe Test**.
2. Add a **Manual Trigger** node.
3. Add an **Edit Fields (Set)** node and connect the trigger to it.
4. Add these fields:
   - `employee` (String): `Operations Manager`
   - `status` (String): `Awaiting Founder Review`
   - `action_executed` (Boolean): `false`
   - `note` (String): `Test only; no external action is performed.`
5. Select **Execute Workflow** and inspect the output. Expected: one item containing all four fields.
6. Save the workflow. Leave it inactive; a manual trigger is sufficient for this test.

## What this proves
It proves that a manual n8n workflow can produce a test record. It does **not** prove that the Python MCP server is connected to n8n, nor does it create a real approval queue.

## Next integration phase
The current Python project runs its MCP server in local stdio mode and stores approval proposals in SQLite. n8n Cloud cannot reach a process running only on a phone or another private computer. Before connecting the two, choose a trusted reachable host or an authenticated adapter and verify its availability, persistence, and access controls. Do not paste secrets into GitHub or chat.

## Founder approval boundary
An approval decision is not execution. Do not connect live email, social publishing, payment, advertising spend, deployment, or destructive operations until there is a separate authenticated founder action that confirms the exact target and payload. Keep test workflows separate from live execution workflows.
