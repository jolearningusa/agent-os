PYTHON ?= .local/harness-lab/config-check-env/bin/python

.PHONY: check
check:
	"$(PYTHON)" scripts/check_docs.py
	"$(PYTHON)" scripts/check_harness_config.py configs/local-hermes.json
	"$(PYTHON)" scripts/check_context_events.py tests/fixtures/context-events.json
	"$(PYTHON)" -m unittest discover -s tests -v
	"$(PYTHON)" -m compileall -q scripts tests
