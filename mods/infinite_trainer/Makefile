# Build NFSMW Infinite Trainer .asi
# Requires: winegcc (Wine development tools) OR i686-w64-mingw32-gcc (MinGW-w64)
#
# winegcc path (default): produces a real PE32 DLL that Wine/Windows can load.

## Build NFSMW Infinite Trainer .asi
##
## Requires MinGW-w64 (32-bit Windows cross-compiler):
##     pacman -S mingw-w64-gcc          # Arch
##     apt install gcc-mingw-w64-i686   # Debian/Ubuntu
##     brew install mingw-w64           # macOS
##
## (winegcc was tried but lacks lib32 import libraries on this distro.
##  MinGW-w64 is the standard tool for this and produces a real PE32 DLL.)

CC      = i686-w64-mingw32-gcc
CFLAGS  = -m32 -Os -Wall -Wextra
LDFLAGS = -shared -static -static-libgcc -Wl,--kill-at
LIBS    = -lkernel32

TARGET  = nfsmw_trainer.asi
SRC     = nfsmw_trainer.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRC) -o $(TARGET) $(LIBS)
	@echo "Built: $(TARGET)"
	@file $(TARGET) || true

clean:
	rm -f $(TARGET) *.o

install: $(TARGET)
	cp $(TARGET) "../../extracted/app/scripts/"
	@echo "Installed to app/scripts/$(TARGET)"

.PHONY: all clean install
