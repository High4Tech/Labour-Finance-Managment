/* Small in-memory list snapshots only. Never persisted, never used to authorize
   a write or to cache financial balances. A mutation invalidates its whole scope. */
export function createReadCache({limit=20,byteLimit=1000000,ttl=15000,now=Date.now}={}){
 const entries=new Map();let bytes=0;
 const remove=key=>{const item=entries.get(key);if(item){bytes-=item.bytes;entries.delete(key);}};
 return {
  get(key){const item=entries.get(key);if(!item)return;if(now()-item.at>=ttl){remove(key);return;}entries.delete(key);entries.set(key,item);return item.value;},
  set(key,value){const size=new TextEncoder().encode(JSON.stringify(value)).length;remove(key);if(size>byteLimit/2)return;entries.set(key,{value,bytes:size,at:now()});bytes+=size;while(entries.size>limit||bytes>byteLimit)remove(entries.keys().next().value);},
  invalidate(scope){for(const key of entries.keys())if(!scope||key.startsWith(scope+'|'))remove(key);},
  stats(){return {entries:entries.size,bytes};}
 };
}
export const readCache=createReadCache();
