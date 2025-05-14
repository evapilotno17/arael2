CC      = clang
CFLAGS  = -O2 -std=c11 -DDEBUG
# CFLAGS  = -O2 -std=c11 
SRC     = keylog.c
OUT     = keylog.exe  # exe because it makes it easier to ignore in vomitignore
LIBS    = -lsqlite3 -framework ApplicationServices # sqlite3 is in default libs; ApplicationServices gives us the event tap

all: $(OUT)

$(OUT): $(SRC)
	$(CC) $(CFLAGS) $(SRC) $(LIBS) -o $(OUT)

clean:
	rm -f $(OUT)
