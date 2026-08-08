# DeepSeek thinking protocol audit

**Status:** official-documentation audit; no model call.

DeepSeek V4 Flash supports thinking and non-thinking on the same model through
`extra_body={"thinking":{"type":"enabled|disabled"}}`. In thinking mode,
`reasoning_content` and final `content` are separate response fields, but both
are generated inside one completion budget. There is no documented parameter
that reserves a separate number of tokens for the final JSON.

The API exposes only `high` and `max` reasoning effort. Compatibility values
`low` and `medium` map to `high`; therefore using a nominally smaller effort
does not provide a documented cheap-thinking condition. Temperature/top-p do
not affect thinking mode. JSON Output is supported, but the prompt must request
JSON and `max_tokens` must be high enough to avoid a truncated object.

This explains the prior failure mode without making a scientific claim: at
128, 512, and often 2,048 output tokens, reasoning consumed the completion
budget before a final JSON was emitted. Brute-force escalation to 4k/8k/16k
over the full factorial arm would be methodologically and financially poor.

Any future thinking test should therefore be tiny and preregistered, inspect
`finish_reason`, `reasoning_tokens`, and final-content presence, and use a hard
experiment cost guard. A successful tiny protocol test would establish only
operability; it would not rescue the incomplete previous factorial arm.

Official references:

- https://api-docs.deepseek.com/api/create-chat-completion
- https://api-docs.deepseek.com/guides/thinking_mode
- https://api-docs.deepseek.com/guides/reasoning_model
- https://api-docs.deepseek.com/guides/json_mode/

