# LLM Agent Navigation Experiments

This document summarizes the text-grid experiments with LLM agents.

## Research Question

Can a language model agent solve a small grid-world navigation task through text feedback, partial observability, and memory, without directly receiving true wall coordinates, chest coordinates, or the player's absolute position?

## Environment

- A deterministic text grid world implemented in Python.
- The player moves on a small 2D grid.
- The target is to find and open a chest.
- The Python environment owns the true map and validates all actions.
- The model receives text feedback, action memory, and later a relative spatial memory built only from executed actions.

## Main Iterations

| Version | Theme | Result |
| --- | --- | --- |
| V001 | Rule-based text grid baseline | Established the playable environment and command loop. |
| V002 | Arrival feedback and interact ability | The agent can be told when it reaches the chest and can open it with `interact`. |
| V003 | Relative spatial memory | The model receives a maintained relative map instead of true coordinates. |
| V004 | Qwen2.5 3B comparison | Larger local model was tested under the same environment. |
| V005 | Lower revisit-count prompt | Added an exploration prior that asks the model to reduce repeated visits. |
| V006 | Cloud model direct control | DeepSeek completed the task quickly, showing the benefit of stronger reasoning. |
| V007 | Mode B: cloud guidance only when stuck | Succeeded with low cloud-call count; DeepSeek provided short-term guidance while Qwen executed steps. |
| V008 | Mode A: fixed-interval cloud planning | Failed despite more cloud calls; reached the chest but did not reliably switch to `interact`. |

## Key Findings

1. Text-only agents can navigate a simple grid, but prompt-only control is brittle.
2. Giving the agent an `interact` action too early can waste steps, because small models may overuse it without knowing when it applies.
3. Relative spatial memory is more maintainable than a plain recent-action log, but it still depends on the local model interpreting it reliably.
4. Strong cloud models can dramatically improve performance, but every-step cloud reasoning is not a realistic robotics-style deployment model.
5. The hybrid architecture is sensitive to the control loop. Mode B worked better than Mode A in the current implementation because event timing mattered more than planning frequency.
6. Stop conditions written into a prompt are not control logic. If a stop condition is important, Python should monitor and enforce it.

## Mode B vs Mode A

Mode B calls the cloud model only when the local model appears stuck. In the successful run, the local model reached the chest and selected `interact`, while the cloud model had only been used a small number of times.

Mode A calls the cloud model at a fixed interval. In the failed run, the cloud plan helped the agent reach the chest, but the five-step planning window was not interrupted when the chest was found. The local model then continued moving and left the chest instead of opening it.

The lesson is that high-level planning should be event-driven:

```text
exploring -> target_found -> opening
```

Once the environment reports that `interact` is available, the controller should suspend exploration and enter a terminal interaction phase.

## Reproducibility

Main files:

- `src/text_world_agent.py`: current text-world implementation.
- `src/hybrid_mode_b.py`: hybrid Mode B implementation.
- `src/hybrid_mode_a.py`: hybrid Mode A implementation.
- `docs/experiment-log.html`: full HTML experiment log.
- `experiments/runs/`: curated run logs.
- `experiments/versions/`: version snapshots.

Local model requirement:

```bash
ollama serve
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b
```

Cloud API keys are read from environment variables:

```bash
export DEEPSEEK_API_KEY="your key"
```

Example runs:

```bash
python3 src/text_world_agent.py --ai --solve --provider deepseek --max-steps 100
python3 src/hybrid_mode_b.py --hybrid-solve --max-steps 100
python3 src/hybrid_mode_a.py --max-steps 100
```

## GitHub Packaging Notes

Generated artifacts such as virtual environments, checkpoints, and ad-hoc run outputs should not be committed. Keep reproducible source files, curated logs, and concise result summaries.
