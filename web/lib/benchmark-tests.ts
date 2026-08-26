export interface BenchmarkTestDefinition {
  id: string
  name: string
  label: string
  desc: string
  defaultOn: boolean
}

export const BENCHMARK_TESTS: BenchmarkTestDefinition[] = [
  {
    id: 'T1',
    name: 'Latency',
    label: 'Latency',
    desc: 'Time-to-first-token (streaming)',
    defaultOn: true,
  },
  {
    id: 'T2',
    name: 'Tool Calling',
    label: 'Tools',
    desc: 'Function call with valid JSON arguments',
    defaultOn: true,
  },
  {
    id: 'T3',
    name: 'Structured Output',
    label: 'Schema',
    desc: 'JSON schema adherence (person record)',
    defaultOn: true,
  },
  {
    id: 'T4',
    name: 'Instruction Following',
    label: 'Instruct',
    desc: 'Follow strict output format constraints',
    defaultOn: true,
  },
  {
    id: 'T5',
    name: 'Reasoning Quality',
    label: 'Reason',
    desc: 'Multi-step logic puzzle (river crossing)',
    defaultOn: true,
  },
  {
    id: 'T6',
    name: 'Context Coherence',
    label: 'Context',
    desc: 'Multi-turn memory retention',
    defaultOn: true,
  },
  {
    id: 'T7',
    name: 'Consistency',
    label: 'Consist.',
    desc: 'Same answer across repeated identical prompts',
    defaultOn: true,
  },
  {
    id: 'T8',
    name: 'Conciseness',
    label: 'Concise',
    desc: 'Response within a specified word limit',
    defaultOn: true,
  },
  {
    id: 'T9',
    name: 'Coding',
    label: 'Coding',
    desc: 'Generate and execute a memoized coding solution',
    defaultOn: false,
  },
  {
    id: 'T10',
    name: 'Long Context',
    label: 'Long ctx',
    desc: 'Retrieve a needle from a long context window',
    defaultOn: false,
  },
  {
    id: 'T11',
    name: 'Multilingual',
    label: 'Multilingual',
    desc: 'Solve a reasoning task in another language',
    defaultOn: false,
  },
  {
    id: 'T12',
    name: 'Throughput',
    label: 'Throughput',
    desc: 'Tokens per second during streaming',
    defaultOn: true,
  },
]

export const DEFAULT_BENCHMARK_TEST_IDS = BENCHMARK_TESTS
  .filter((test) => test.defaultOn)
  .map((test) => test.id)
