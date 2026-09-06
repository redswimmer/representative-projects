// Single source for the output contract: schema.json feeds the model twice
// (constrained decoding + prompt injection) and the grader once (is-json).
// JS config because YAML cannot file://-reference a schema inside provider config.
const schema = require('./schema.json');

module.exports = {
  description: 'Phase 2: propose one representative project from verified problems',
  sharing: false,
  prompts: ['file://prompts/propose.txt'],
  providers: [
    {
      id: 'anthropic:claude-agent-sdk',
      label: 'claude-agent-sdk',
      config: {
        apiKeyRequired: false, // auth = the local Claude Code login (subscription)
        model: 'claude-sonnet-5', // pin explicitly; SDK default drifts with the account
        title: 'representative-projects', // fixed session title; skips the auto-title model call
        // Constrained decoding: malformed JSON impossible by construction.
        // Adopted after error analysis observed a ~10-13% malformed rate.
        output_format: { type: 'json_schema', schema },
      },
    },
  ],
  defaultTest: {
    vars: {
      schema: JSON.stringify(schema, null, 2), // rendered into the prompt as {{schema}}
      num_projects: '3', // hard-set for evals; integrity.py enforces the count
    },
    assert: [
      { type: 'is-json', value: schema, metric: 'schema_adherence' },
      { type: 'python', value: 'file://asserts/integrity.py', metric: 'integrity' },
    ],
  },
  tests: [
    {
      path: 'file://generate_tests.py:generate_tests',
      config: { fixtures_dir: 'fixtures', job_listings_dir: '../../job_listings' },
    },
  ],
};
