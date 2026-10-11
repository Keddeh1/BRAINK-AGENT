.PHONY: test serve check package
test:
	python3 scripts/native-ci.py
serve:
	python3 -m braink_agent serve
check:
	python3 scripts/verify-source.py
	node --check web/app.js
package:
	python3 scripts/package.py
