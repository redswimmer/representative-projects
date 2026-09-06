// Single source for the output contract: schema.json feeds the model twice
// (constrained decoding + prompt injection) and the grader once (is-json).
// JS config because YAML cannot file://-reference a schema inside provider config.
const schema = require('./schema.json');

module.exports = {
  description: 'Phase 3: ground each proposed project in company-published sources',
  sharing: false,
  prompts: ['file://prompts/research.txt'],
  providers: [
    {
      id: 'anthropic:claude-agent-sdk',
      label: 'claude-agent-sdk',
      config: {
        apiKeyRequired: false, // auth = the local Claude Code login (subscription)
        model: 'claude-sonnet-5', // pin explicitly; SDK default drifts with the account
        title: 'representative-projects', // fixed session title; skips the auto-title model call
        // Research surface = the public web, nothing else: replaces the default
        // read-only tool set entirely (probe-verified to compose with output_format).
        custom_allowed_tools: ['WebSearch', 'WebFetch'],
        // Constrained decoding: malformed JSON impossible by construction.
        output_format: { type: 'json_schema', schema },
      },
    },
  ],
  defaultTest: {
    vars: {
      schema: JSON.stringify(schema, null, 2), // rendered into the prompt as {{schema}}
      company: 'Anthropic', // corpus-level fact: every committed listing is an Anthropic listing
    },
    assert: [
      { type: 'is-json', value: schema, metric: 'schema_adherence' },
    ],
  },
  tests: [
    {
      path: 'file://generate_tests.py:generate_tests',
      config: { fixtures_dir: 'fixtures' },
    },
  ],
};
