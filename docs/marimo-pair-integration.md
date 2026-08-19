# marimo-pair Agent Integration

This document describes how to use marimo-pair with OpenCode for agent-assisted notebook development.

## Setup

1. Install marimo with pair programming support:
```bash
uv pip install marimo
```

2. The `marimo pair` command is built into marimo 0.23+.

## Usage with OpenCode

### Starting a Pair Programming Session

```bash
# Start marimo notebook server
marimo run notebooks/11_core.py --port 2718 --no-token --headless

# In another terminal, generate the pair programming prompt
marimo pair prompt --url http://localhost:2718 --file notebooks/11_core.py --opencode
```

### Using the Generated Prompt

The `marimo pair prompt --opencode` command generates a prompt that you can copy and paste into OpenCode. The prompt includes:

- The current notebook state
- The marimo kernel connection details
- Instructions for the agent on how to interact with the notebook

### Using the Helper Script

A helper script is provided at `scripts/marimo-pair.sh`:

```bash
# Start a pair programming session for a specific notebook
./scripts/marimo-pair.sh notebooks/11_core.py
```

This script:
1. Starts marimo run in the background
2. Generates the OpenCode pair programming prompt
3. Waits for you to stop the server

## Agent Capabilities

With marimo-pair, the OpenCode agent can:

1. **Read notebook state** - See all cells, outputs, and variables
2. **Edit cells** - Modify code cells, markdown cells
3. **Execute cells** - Run cells and see outputs
4. **Add/delete cells** - Restructure the notebook
4. **Debug** - Inspect variables, trace errors

## Example Workflow

```bash
# Terminal 1: Start marimo
marimo run notebooks/11_core.py --port 2718 --no-token

# Terminal 2: Generate prompt and start OpenCode
marimo pair prompt --url http://localhost:2718 --file notebooks/11_core.py --opencode
# Copy the generated prompt
opencode
# Paste prompt in OpenCode

# Now you can ask OpenCode to:
# - "Add a test for the HECSS class"
# - "Fix the bug in estimate_width_scale"
# - "Add documentation for the sample method"
# - "Refactor the _sampler_ser method"
```

## Integration with CI/CD

The marimo-pair integration works well with the CI/CD pipeline:

1. **Development**: Use marimo-pair for interactive development
2. **Testing**: Run `make check` to validate notebooks
3. **Documentation**: Run `make build-docs` to generate docs
4. **CI**: GitHub Actions runs tests and builds docs automatically

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 2718
lsof -ti:2718 | xargs kill -9
```

### Authentication Issues
If you get authentication errors, use `--no-token` flag:
```bash
marimo run notebooks/11_core.py --port 2718 --no-token --headless
```

### Connection Refused
Make sure marimo is running before generating the prompt:
```bash
# Check if marimo is running
curl http://localhost:2718/api/status
```

## Resources

- [marimo Documentation](https://docs.marimo.io/)
- [marimo-pair Documentation](https://docs.marimo.io/guides/pair_programming/)
- [OpenCode Documentation](https://opencode.ai/)