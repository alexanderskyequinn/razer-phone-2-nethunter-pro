/* Exercise the real upstream switching function against in-memory phone GPTs.
 * All filesystem lookup and GPT writes are replaced by explicit test stubs. */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include "slot-fixtures.h"
static int fake_stat(const char *path, struct stat *st);
#define stat(path, buffer) fake_stat(path, buffer)
#include "bootctrl_impl.c"
#undef stat

static unsigned char primary[FIXTURE_COUNT][128], backup[FIXTURE_COUNT][128];
static unsigned char touched[FIXTURE_COUNT];
static int commits;
static int index_for(const char *name) {
 for(int i=0;i<FIXTURE_COUNT;++i)if(!strcmp(name,fixture_names[i]))return i;
 return -1;
}
static int fake_stat(const char *path,struct stat *st) {
 const char *name=strrchr(path,'/');
 if(!name||index_for(name+1)<0){errno=ENOENT;return -1;}
 memset(st,0,sizeof(*st));st->st_mode=S_IFBLK;return 0;
}
int gpt_disk_get_disk_info(const char *name,struct gpt_disk *disk) {
 (void)disk;return index_for(name)<0?-1:0;
}
uint8_t *gpt_disk_get_pentry(struct gpt_disk *disk,const char *name,enum gpt_instance which) {
 (void)disk;int i=index_for(name);if(i<0)return NULL;
 touched[i]=1;return which==PRIMARY_GPT?primary[i]:backup[i];
}
int gpt_disk_commit(struct gpt_disk *disk){(void)disk;++commits;return 0;}

int main(void) {
 memcpy(primary,fixture_entries,sizeof(primary));
 memcpy(backup,fixture_entries,sizeof(backup));
 unsigned transitions[]={0,1,1,0,0,1};
 for(unsigned t=0;t<sizeof(transitions)/sizeof(transitions[0]);++t){
  struct gpt_disk disk={0};unsigned slot=transitions[t];
  assert(!boot_ctl_set_active_slot_for_partitions(&disk,slot));
  assert(!memcmp(primary,backup,sizeof(primary)));
  for(int i=0;i<FIXTURE_COUNT;++i){
   /* Unique GUID, start/end LBAs, name and all non-AB flags stay intact. */
   for(unsigned b=16;b<128;++b)if(b!=AB_FLAG_OFFSET)
    assert(primary[i][b]==fixture_entries[i][b]);
   if(!touched[i]){assert(!memcmp(primary[i],fixture_entries[i],128));continue;}
   size_t len=strlen(fixture_names[i]);assert(len>2);
   char other[73];strcpy(other,fixture_names[i]);
   int is_a=other[len-1]=='a';other[len-1]=is_a?'b':'a';
   int pair=index_for(other);assert(pair>=0);
   int was_active=(fixture_entries[i][AB_FLAG_OFFSET]&4)!=0;
   int should_active=is_a?(slot==0):(slot==1);
   const unsigned char *expected_guid=was_active==should_active?fixture_entries[i]:fixture_entries[pair];
   assert(!memcmp(primary[i],expected_guid,16));
   assert(((primary[i][AB_FLAG_OFFSET]&4)!=0)==should_active);
   if(should_active)assert(primary[i][AB_FLAG_OFFSET]==0x3f);
  }
 }
 assert(commits==6);
 puts("PASS: real slot-switch function, A/B and repeated selection, both GPT copies, canonical GUIDs, retries, unchanged partition geometry and payload identifiers");
 return 0;
}
