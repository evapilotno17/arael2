/* ./macos/keylog */

#define _POSIX_C_SOURCE 199309L

#include <ApplicationServices/ApplicationServices.h>
#include <errno.h>
#include <signal.h>
#include <sqlite3.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define DB_DIR  "../keydb"
#define DB_PATH DB_DIR "/keys.db"
#define BATCH   1 // we need synced logging for concurrent microprocesses

static volatile sig_atomic_t stop = 0;
static sqlite3 *db=NULL; static sqlite3_stmt *st=NULL; static int queued=0;

/* ---------- helpers ---------- */
static void fatal(const char *m){ perror(m); exit(EXIT_FAILURE); }
static void ensure_db_dir(void){ if(access(DB_DIR,F_OK)==-1 && mkdir(DB_DIR,0700)==-1 && errno!=EEXIST) fatal("mkdir db"); }
static int64_t now_us(void){ struct timeval tv; gettimeofday(&tv,0); return (int64_t)tv.tv_sec*1000000LL+tv.tv_usec; }
static void flush_batch(void){ if(queued){ sqlite3_exec(db,"commit; begin;",0,0,0); queued=0; } }
static void handle_sig(int sig){ (void)sig; stop=1; }

/* ---------- event‑tap callback ---------- */
static CGEventRef tap_cb(CGEventTapProxy p,CGEventType t,CGEventRef e,void*ctx){
    if(t==kCGEventKeyDown){
        sqlite3_bind_int64(st,1,now_us());
        sqlite3_bind_int  (st,2,(int)CGEventGetIntegerValueField(e,kCGKeyboardEventKeycode));
        sqlite3_bind_text (st,3,"macos",-1,SQLITE_STATIC);
        sqlite3_step(st); sqlite3_reset(st);
        if(++queued>=BATCH) flush_batch();
    }
    if(stop){ CFRunLoopStop(CFRunLoopGetCurrent()); return NULL; }
    return e;
}

int main(void)
{
    signal(SIGINT,handle_sig); signal(SIGTERM,handle_sig);
    signal(SIGHUP,handle_sig); signal(SIGQUIT,handle_sig);

    ensure_db_dir();

    /* open / init sqlite */
    if(sqlite3_open(DB_PATH,&db)!=SQLITE_OK) fatal("sqlite open");
    sqlite3_exec(db,"pragma journal_mode=WAL;",0,0,0);
    sqlite3_exec(db,
        "create table if not exists keystrokes("
        " ts_us integer,"
        " code  integer,"
        " os    text);",
        0,0,0);
    if(sqlite3_prepare_v2(db,"insert into keystrokes(ts_us, code, os) values (?,?,?);",-1,&st,0)!=SQLITE_OK) fatal("prepare");
    sqlite3_exec(db,"begin;",0,0,0);

    /* install event tap */
    CGEventMask mask=CGEventMaskBit(kCGEventKeyDown);
    CFMachPortRef tap=CGEventTapCreate(kCGSessionEventTap,kCGHeadInsertEventTap,0,mask,tap_cb,NULL);
    if(!tap) fatal("event tap");

    CFRunLoopSourceRef src=CFMachPortCreateRunLoopSource(kCFAllocatorDefault,tap,0);
    CFRunLoopAddSource(CFRunLoopGetCurrent(),src,kCFRunLoopCommonModes);
    CGEventTapEnable(tap,true);

    CFRunLoopRun();                 /* blocks until stop==1 */

    /* graceful shutdown */
    flush_batch(); sqlite3_finalize(st); sqlite3_close(db);
    fprintf(stderr,"\n[clean exit] keystrokes saved. goodbye.\n");
    return 0;
}
