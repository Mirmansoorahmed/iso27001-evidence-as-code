export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: demo test validate ci fmt

demo:
	eac demo

test:
	pytest

fmt:
	terraform -chdir=lz fmt -recursive

validate:
	terraform -chdir=lz fmt -check -recursive
	terraform -chdir=lz init -backend=false -input=false
	terraform -chdir=lz validate

ci: validate test
