# terminal-bench-task

![verify](https://github.com/barringtonpopo/terminal-bench-task/actions/workflows/verify.yml/badge.svg)

One original agent-evaluation task in the [Harbor](https://harborframework.com) format, the successor to the [Terminal-Bench](https://www.tbench.ai) task layout, plus a verifier that re-proves the task from scratch. Not affiliated with either project, just built to their spec.

## Why this exists

Building terminal tasks for agent evaluation is part of my day job, and that work sits under NDA. This is the public artefact: one complete task, authored end to end, with the quality checks I'd want any task to pass before it grades a model.

## The task

`funding-spread-report` drops the agent into a container with funding rate observations from two perpetual futures venues in two different shapes: gzipped JSON lines with ISO timestamps on one side, CSV with epoch milliseconds and suffixed tickers on the other. The job is a desk chore: most recent observation per asset per venue, annualise, compute cross-venue spreads, and write an exactly specified CSV.

The terrain does the discriminating. Every asset ships with decoy earlier observations, so averaging or taking the first row seen produces wrong numbers. One asset's most recent row has an empty rate field, and the instruction's stated rule is to fall back to the latest valid observation, so treating empty as zero fails a dedicated test. Some rates carry stray whitespace, one line is duplicated verbatim, six assets exist on only one venue, and the output has exact formatting, rounding and ordering requirements. Difficulty is meant as medium: nothing exotic, several ways to be almost right.

## Format

The layout follows current Harbor conventions rather than the older Terminal-Bench ones: the instruction lives in its own `instruction.md`, configuration in `task.toml`, the environment definition under `environment/`, the oracle in `solution/solve.sh`, and the tests in `tests/` with a `test.sh` that writes the reward to `/logs/verifier/reward.txt`. Tests and solution are never part of the image, they get injected at runtime, which is the structural fix Harbor made to stop agents reading the answers.

## Design decisions worth naming

The instruction specifies every correct end state, including the empty-rate rule, because an agent cannot infer a spec decision, only follow one. The task carries two independent implementations of that spec: a reference implementation in `tools/compute_expected.py` that derives the test expectations, and the oracle in `solution/solve.sh`, written separately. The verifier proves they agree, which is cheap insurance against the task author misreading his own spec.

The input data is committed, not generated inside the image, and `tools/gen_data.py` regenerates it byte for byte, gzip header pinned, so the environment cannot drift. The generator also refuses any rate whose graded value lands near a .05 rounding boundary, so float behaviour can never flip a verdict. A hygiene check confirms the Dockerfile references neither tests nor solution, mirroring the benchmark's own CI. And every artefact carries a canary string, the convention that lets dataset builders exclude evaluation material from training corpora.

## Verification

```bash
python3 verify.py
```

Seventeen checks across four families: the Harbor structure is present, the hygiene rules hold, the data regenerates identically, and the fail-then-pass loop works in a fresh directory, tests failing before the oracle runs and passing after. CI runs the same script on every push, so the badge means the task still discriminates.

## Running it with Docker

Build the environment, then run the two halves of the demonstration. The tests and solution are mounted read-only at runtime, never baked in:

```bash
cd funding-spread-report
docker build -t funding-task environment

docker run --rm -v "$PWD/tests:/tests:ro" funding-task \
  bash -c 'bash /tests/test.sh; echo "reward: $(cat /logs/verifier/reward.txt)"' 
```

That first run ends with `reward: 0`, the task in its unsolved state. Then let the oracle loose first:

```bash
docker run --rm -v "$PWD/solution:/solution:ro" -v "$PWD/tests:/tests:ro" funding-task \
  bash -c 'bash /solution/solve.sh && bash /tests/test.sh; echo "reward: $(cat /logs/verifier/reward.txt)"' 
```

That one ends with `reward: 1`. The reward file is the whole interface: an agent harness reads nothing else. To run the task under the real harness, point Harbor at the task directory, per its [docs](https://harborframework.com/docs).

## Licence

MIT.

## Roadmap

A second task in a different category, an adapter run recording how current frontier agents score against it, and publication to the Harbor hub.
