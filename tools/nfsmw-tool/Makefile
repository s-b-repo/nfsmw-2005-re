## nfsmw-tool — install symlink so the script runs as `nfsmw-tool` from anywhere.
## Pure Python, no compilation needed. Requires Python 3.10+.

PREFIX ?= $(HOME)/.local

HERE := $(shell pwd)

all: nfsmw-tool

nfsmw-tool: nfsmw_tool.py
	@chmod +x nfsmw_tool.py
	@ln -sf "$(HERE)/nfsmw_tool.py" nfsmw-tool
	@echo "Built: $(HERE)/nfsmw-tool"

install: nfsmw-tool
	@mkdir -p "$(PREFIX)/bin"
	@ln -sf "$(HERE)/nfsmw_tool.py" "$(PREFIX)/bin/nfsmw-tool"
	@echo "Installed: $(PREFIX)/bin/nfsmw-tool"
	@echo "Make sure $(PREFIX)/bin is in your PATH."

uninstall:
	rm -f $(PREFIX)/bin/nfsmw-tool

test: nfsmw-tool
	@echo "Testing bChunk hash..."
	@./nfsmw-tool hash MASS | grep -q '0x4A56503D' && echo "  ✓ bChunk(MASS) = 0x4A56503D"
	@./nfsmw-tool hash BASE | grep -q '0xA6B47FAC' && echo "  ✓ bChunk(BASE) = 0xA6B47FAC"
	@echo "Testing reverse lookup..."
	@./nfsmw-tool lookup 0x4A56503D | grep -q 'MASS' && echo "  ✓ lookup(0x4A56503D) finds MASS"
	@echo "Testing stats..."
	@./nfsmw-tool stats | head -3
	@echo "All tests passed."

clean:
	rm -f nfsmw-tool

.PHONY: all install uninstall test clean
