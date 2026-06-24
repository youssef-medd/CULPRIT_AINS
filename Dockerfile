# Culprit — Python evaluation pipeline, fully baked so anyone can run it with
# zero local setup (no venv, no Python-version juggling). The pipeline runs
# deterministically with NO API key; pass NVIDIA_API_KEY at runtime to switch
# the agent + judges onto a real LLM.
#
#   docker build -t culprit .
#   docker run --rm culprit                          # runs on the bundled tickets
#   docker run --rm -e NVIDIA_API_KEY=nvapi-... culprit
#   docker run --rm culprit python -m culprit.meta_eval   # judging-the-judges
#   docker run --rm culprit pytest -q                     # the test suite
FROM python:3.11-slim

# Faster, cleaner Python in a container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so the layer caches across source-only changes.
# pyproject defines the optional groups; [agent] pulls the only hard runtime
# deps (langgraph, langchain-core, openai), [dev] lets you run pytest in-image.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install -e ".[agent,dev]"

# Bundle the synthetic fixtures + contracts so the default run works out of the box.
COPY data ./data
COPY tests ./tests

# The LLM judges are the mechanism. Run with a key to exercise the real
# evaluation path:
#   docker run --rm -e NVIDIA_API_KEY=nvapi-... culprit
# Without a key the pipeline still runs end-to-end on the deterministic
# stand-in (reproducibility mode); culprit.run prints which backend is active
# so the two are never confused.
CMD ["python", "-m", "culprit.run", "--tickets", "data/synthetic/tickets.jsonl"]
