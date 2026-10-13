# Run order. Each target is one numbered script; each script can also run on its own.
PY ?= python3
V  ?= 1.0

.PHONY: fetch triage extract validate harmonize qa figures final test gate all

fetch:      ; $(PY) code/01_fetch.py
extract:    ; $(PY) code/02_extract.py
triage:     ; $(PY) code/02_extract.py --all-screened && $(PY) code/02b_triage.py
validate:   ; $(PY) code/03_validate.py
harmonize:  ; $(PY) code/04_harmonize.py --version $(V)
qa:         ; $(PY) code/05_qa.py --version $(V)
figures:    ; $(PY) code/06_figures.py --version $(V)
final:      ; $(PY) code/06_figures.py --version $(V) --final
test:       ; $(PY) -m unittest discover -s tests -v
gate:       ; $(PY) tools/publish_gate.py .

# After curation: validate -> harmonize -> QA -> figures
all: validate harmonize qa figures
