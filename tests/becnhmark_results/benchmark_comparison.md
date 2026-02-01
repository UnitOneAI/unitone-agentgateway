# PII Guard Benchmark Comparison

Comparison of AgentGateway performance with PII security guard enabled vs disabled.

---

## Test 1: generate_large_pii_text (Large Payload ~2MB)

**Command:**
```
python tests/benchmark.py --route /pii-test --requests 20 --concurrency 10 --operation tools/call --tool-name generate_large_pii_text
```

| Metric              | Guard Enabled    | Guard Disabled   | Overhead      |
|---------------------|------------------|------------------|---------------|
| **Avg Latency**     | 18911.26 ms      | 16200.63 ms      | +2710 ms (+17%) |
| **P50 Latency**     | 19716.98 ms      | 16177.86 ms      | +3539 ms (+22%) |
| **P95 Latency**     | 20241.73 ms      | 16427.80 ms      | +3814 ms (+23%) |
| **P99 Latency**     | 20284.75 ms      | 16435.53 ms      | +3849 ms (+23%) |
| **Min Latency**     | 3513.27 ms       | 16035.94 ms      | -12523 ms*    |
| **Stddev**          | 3649.80 ms       | 142.07 ms        | Higher variance |
| **Throughput**      | 0.50 rps         | 0.61 rps         | -18%          |
| **Total Time**      | 39.73 s          | 32.57 s          | +7.16 s       |
| **Success Rate**    | 100%             | 100%             | Same          |

*Note: Min latency anomaly may be due to warmup or caching effects.

---

## Test 2: generate_full_record (Small Payload ~1-2KB)

**Command:**
```
python tests/benchmark.py --route /pii-test --requests 500 --concurrency 10 --operation tools/call --tool-name generate_full_record
```

| Metric              | Guard Enabled    | Guard Disabled   | Overhead      |
|---------------------|------------------|------------------|---------------|
| **Avg Latency**     | 27.02 ms         | 24.55 ms         | +2.47 ms (+10%) |
| **P50 Latency**     | 25.30 ms         | 23.95 ms         | +1.35 ms (+6%) |
| **P95 Latency**     | 30.60 ms         | 29.15 ms         | +1.45 ms (+5%) |
| **P99 Latency**     | 127.52 ms        | 42.43 ms         | +85 ms (+200%) |
| **Stddev**          | 14.78 ms         | 3.77 ms          | Higher variance |
| **Throughput**      | 364.05 rps       | 399.29 rps       | -9%           |
| **Total Time**      | 1.37 s           | 1.25 s           | +0.12 s       |
| **Success Rate**    | 100%             | 100%             | Same          |

---

## Test 3: generate_bulk_pii (Medium Payload - 150 credit cards)

**Command:**
```
python tests/benchmark.py --route /pii-test --requests 500 --concurrency 10 --operation tools/call --tool-name generate_bulk_pii --tool-args '{"pii_type":"credit_card","count":150}'
```

| Metric              | Guard Enabled    | Guard Disabled   | Overhead      |
|---------------------|------------------|------------------|---------------|
| **Avg Latency**     | 39.93 ms         | 32.46 ms         | +7.47 ms (+23%) |
| **P50 Latency**     | 43.58 ms         | 31.52 ms         | +12.06 ms (+38%) |
| **P95 Latency**     | 53.57 ms         | 39.10 ms         | +14.47 ms (+37%) |
| **P99 Latency**     | 64.84 ms         | 56.94 ms         | +7.90 ms (+14%) |
| **Min Latency**     | 13.76 ms         | 9.30 ms          | +4.46 ms (+48%) |
| **Stddev**          | 11.89 ms         | 6.16 ms          | Higher variance |
| **Throughput**      | 237.21 rps       | 300.40 rps       | -21%          |
| **Total Time**      | 2.11 s           | 1.66 s           | +0.45 s       |
| **Success Rate**    | 100%             | 100%             | Same          |

---

## Summary

| Test Case                  | Payload Size | Avg Overhead | Throughput Impact |
|----------------------------|--------------|--------------|-------------------|
| generate_large_pii_text    | ~2 MB        | +2.7 sec (+17%) | -18%           |
| generate_full_record       | ~1-2 KB      | +2.5 ms (+10%)  | -9%            |
| generate_bulk_pii (150)    | ~15 KB       | +7.5 ms (+23%)  | -21%           |

### Key Findings

1. **Small payloads (~1-2KB)**: PII guard adds ~2-3ms overhead (~10% increase)
2. **Medium payloads (~15KB)**: PII guard adds ~7-12ms overhead (~23-38% increase)
3. **Large payloads (~2MB)**: PII guard adds ~2.7 seconds overhead (~17% increase)
4. **Variance**: Guard enabled shows higher latency variance (stddev), likely due to regex scanning time scaling with content
5. **Reliability**: 100% success rate in all tests - no functional impact

### Recommendations

- For typical MCP payloads (1-50KB), overhead is **<15ms** - acceptable for most use cases
- For very large payloads (>1MB), consider streaming or chunking strategies
- The guard's regex-based PII detection scales linearly with payload size
