.PHONY: install test eval tune bench guard loop

install:        ## install package + dev deps
	pip install -e ".[dev]"

test:           ## run unit + regression tests
	pytest -q

eval:           ## score the current default policy on the labeled dataset
	python bench/eval.py --per-kind 40

tune:           ## grid-search for a better policy
	python bench/eval.py --tune

bench:          ## token-savings benchmark on a screenshot trace
	python bench/make_synthetic_trace.py
	python bench/harness.py

guard:          ## fail if accuracy/safety regressed (use in CI / Claude Code loop)
	pytest -q tests/test_accuracy.py tests/test_decide.py

## The self-improving loop: measure -> search -> validate -> guard.
## Run `make loop` (or drive it from Claude Code's /loop) to re-tune whenever the
## dataset grows with new hard cases.
loop: eval tune test
	@echo "loop complete — see TOP CONFIGS above; bake the winner into glance/policy.py"
