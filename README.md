# LLM Agent Navigation Experiments

Text-first navigation experiments for studying how language-model agents behave in a small grid world under partial observability, memory, local/cloud model splits, and different planning loops.

The project started from a simple question:

> Can an LLM-driven agent find and open a chest in a grid world without seeing the true map, wall coordinates, chest coordinates, or its absolute position?

## What This Repository Contains

```text
src/text_world_agent.py
  Main text-world agent experiment. Supports local Ollama models and cloud APIs.

src/hybrid_mode_b.py
  Mode B: local low-capability model executes each step; cloud model gives guidance only when the local agent appears stuck.

src/hybrid_mode_a.py
  Mode A: cloud model gives fixed-interval high-level plans; local model executes each step.

docs/experiment-summary.md
  Research summary, iteration history, and conclusions.

docs/experiment-log.html
  Full HTML experiment log generated during the original exploration.

experiments/runs/
  Curated run logs from completed experiments.

experiments/versions/
  Python snapshots for each experiment version.
```

## Core Ideas

- The Python environment owns the true grid map and validates all actions.
- The model does not receive true wall coordinates, chest coordinates, or absolute player coordinates.
- The agent receives text feedback from the environment after each action.
- Later versions add relative spatial memory built only from executed actions and collision feedback.
- `interact` becomes available only when the player reaches the chest.
- Hybrid experiments compare fixed-interval planning against event-triggered cloud guidance.

## Requirements

- Python 3.10+
- Optional local model runtime: [Ollama](https://ollama.com/)
- Optional cloud API: DeepSeek-compatible or Gemini-compatible API key

The Python code uses only the standard library.

For local Qwen experiments:

```bash
ollama serve
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b
```

For DeepSeek experiments:

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

For Gemini experiments:

```bash
export GEMINI_API_KEY="your_api_key"
```

Never commit API keys to the repository.

## Quick Start

Run the basic text world without AI:

```bash
python3 src/text_world_agent.py
```

Run an autonomous local-model solve:

```bash
python3 src/text_world_agent.py --ai --solve --provider ollama --model qwen2.5:1.5b --max-steps 100
```

Run with DeepSeek as the acting model:

```bash
python3 src/text_world_agent.py --ai --solve --provider deepseek --max-steps 100
```

Run hybrid Mode B:

```bash
python3 src/hybrid_mode_b.py --hybrid-solve --max-steps 100
```

Run hybrid Mode A:

```bash
python3 src/hybrid_mode_a.py --max-steps 100
```

Save logs:

```bash
python3 -u src/hybrid_mode_b.py --hybrid-solve --max-steps 100 > hybrid-run-local.txt 2>&1
python3 -u src/hybrid_mode_a.py --max-steps 100 > mode-a-run-local.txt 2>&1
```

## Experiment Summary

| Version | Theme | Result |
| --- | --- | --- |
| V001 | Rule-based text grid baseline | Established the environment and command loop. |
| V002 | Arrival feedback and delayed `interact` | The agent can be told when it reaches the chest and can open it. |
| V003 | Relative spatial memory | Added a coordinate-free relative memory generated from real executed actions. |
| V004 | Qwen2.5 3B comparison | Tested a larger local model under the same environment. |
| V005 | Lower revisit-count prompt | Added an exploration prior to reduce repeated visits. |
| V006 | Cloud model direct control | DeepSeek solved the task quickly, showing the value of stronger reasoning. |
| V007 | Mode B: cloud guidance when stuck | Succeeded with low cloud-call count. |
| V008 | Mode A: fixed-interval cloud planning | Failed despite more cloud calls; reached the chest but did not reliably switch to `interact`. |

Detailed notes are in [docs/experiment-summary.md](docs/experiment-summary.md). The full HTML log is available at [docs/experiment-log.html](docs/experiment-log.html).

## Main Finding

The experiments suggest that stronger models help, but control-loop design matters as much as model capability.

Mode B performed better than Mode A in the current implementation because it is event-triggered. Mode A used more cloud calls, but its five-step planning window was not interrupted when the agent reached the chest. The local model moved away instead of executing `interact`.

This distinction is important:

```text
Prompt stop condition != program control condition
```

If a stop condition is critical, the Python controller should monitor and enforce it.

## Recommended Next Iteration

The next LLM-agent version should add an explicit task-state controller:

```text
exploring -> target_found -> opening -> done
```

When the environment reports that `interact` is available, the controller should suspend exploration and enter an opening phase. This does not expose the chest coordinate; it only turns an environment event into reliable control state.

## Relationship to DQN Work

This repository focuses only on the LLM-agent track. A separate DQN track can compare learned policies against language-model agents under similar grid-world tasks.

## License

No license has been selected yet. Add a license before public release if you want others to reuse the code.
