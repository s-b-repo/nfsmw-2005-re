## lua-disasm — install symlink so the script runs as `lua-disasm` from anywhere.
## Pure Python, no compilation needed. Requires Python 3.10+.

PREFIX ?= $(HOME)/.local

HERE := $(shell pwd)

all: lua-disasm

# Relative symlink so the repo is portable (works after git clone).
lua-disasm: lua_disasm.py
	@chmod +x lua_disasm.py
	@ln -sf lua_disasm.py lua-disasm
	@echo "Built: $(HERE)/lua-disasm"

# Install symlinks an absolute path because $(PREFIX)/bin may be anywhere.
install: lua-disasm
	@mkdir -p "$(PREFIX)/bin"
	@ln -sf "$(HERE)/lua_disasm.py" "$(PREFIX)/bin/lua-disasm"
	@echo "Installed: $(PREFIX)/bin/lua-disasm"
	@echo "Make sure $(PREFIX)/bin is in your PATH."

uninstall:
	rm -f $(PREFIX)/bin/lua-disasm

# Smoke-test: find at least one chunk in gameplay.bun, dump it, decode it.
# Override BUNDLE on the command line if your layout differs.
BUNDLE ?= ../../extracted/app/GLOBAL/decompressed_lzc/gameplay.bun

test: lua-disasm
	@echo "Scanning $(BUNDLE) for Lua chunks..."
	@./lua-disasm find "$(BUNDLE)" | head -5
	@echo "OK."

clean:
	rm -f lua-disasm

.PHONY: all install uninstall test clean
