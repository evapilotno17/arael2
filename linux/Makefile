CC      = gcc
CFLAGS  = -O2 -std=c11 -DDEBUG
# CFLAGS  = -O2 -std=c11
LIBS    = -lsqlite3
SRC     = keylog.c
OUT     = keylog.exe # exe because it makes it easier to ignore in vomitignore

all: $(OUT)

$(OUT): $(SRC)
	$(CC) $(CFLAGS) $(SRC) $(LIBS) -o $(OUT)

clean:
	rm -f $(OUT)
