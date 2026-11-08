# Contributing

Bug reports, masks that trace badly, and pull requests are all welcome.

## Reporting a problem

Open an issue with the version (`fine-tracing --version`), the command you ran, and if you can, the mask (and photo) that went wrong. A mask that traces badly is the most useful thing you can send; crop it if the rest is private.

## Working on the code

```bash
git clone https://github.com/Kronbii/fine-crack-tracing.git
cd fine-crack-tracing
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q                          # the test suite
ruff check src tests scripts       # lint
ruff format src tests scripts      # format
```

Anything that changes what the tracer outputs should keep the benchmark honest:

```bash
fine-tracing bench -o bench/ -j 8  # every tracer on fresh synthetic cracks
```

Compare `bench/summary.md` with [docs/benchmark.md](docs/benchmark.md) before and after. If the numbers move, update `docs/benchmark.md`, the results in the README, and the figures:

```bash
python scripts/make_figures.py --bench bench/ --real <dataset folder>
```

`--real` is a folder with the `BW/` masks and `rgb/` photos of the [Concrete Crack Segmentation Dataset](https://data.mendeley.com/datasets/jwsn7tfbrp/1); without it the real-photo figures are skipped. `scripts/real_check.py <dataset>/BW` reruns the real-mask check.

## Pull requests

- One change per pull request, with a test when it fixes a bug.
- Commit messages say the outcome in plain words: `fix: widths at the image border are exact`, `docs: ...`, `feat: ...`.
- CI runs ruff and pytest on Python 3.10, 3.12 and 3.13, then builds the wheel and traces the examples with it.
