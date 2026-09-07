# Release Checklist

Before publishing this project on GitHub:

- Confirm that no API keys appear in source, logs, shell history snippets, or screenshots.
- Keep `.venv/`, checkpoints, and ad-hoc local run outputs out of git.
- Decide whether to add a license.
- Add a short repository description.
- Optionally add screenshots or terminal excerpts to the README.
- Run syntax checks:

```bash
python3 -m py_compile src/text_world_agent.py src/hybrid_mode_a.py src/hybrid_mode_b.py
```

- Optional smoke tests without cloud APIs:

```bash
python3 src/text_world_agent.py
python3 src/text_world_agent.py --ai --solve --provider ollama --model qwen2.5:1.5b --max-steps 20
```

