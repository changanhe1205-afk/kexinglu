"""Transport-independent optimistic sync. Conflict leaves both versions untouched."""
import hashlib
import json
from uuid import uuid4
from cloud_client import CloudError

def digest(data):
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def synchronize(local, remote, progress=None):
    """local implements snapshots/meta/ack/apply; remote implements put/list/materialize.

    No timestamps decide winners. A local editor racing a download is protected by
    local.apply's transactional expected-hash check. Conflicts remain pending.
    """
    count={'uploaded':0,'downloaded':0,'conflicts':[],'failures':[],'cloud_records':0}
    report=progress or (lambda *args:None)
    report('正在检查本地资料',0,0)
    snapshots=local.snapshots();meta=local.metadata()
    keys=sorted(set(snapshots)|set(meta))
    for index,key in enumerate(keys):
        report('上传记录',index,len(keys))
        data=snapshots.get(key);old=meta.get(key)
        signature=digest(data)
        if old and old['hash']==signature:continue
        if not old:
            old=local.register(key,str(uuid4()));meta[key]=old
        try:
            result=remote.put(old['rid'],key[0],data,old['revision'])
        except (CloudError,OSError,ValueError) as exc:
            count['failures'].append({'key':key,'reason':str(exc) if isinstance(exc,CloudError) else '记录或图片传输失败，请重试'})
            continue
        if not result['accepted']:
            count['conflicts'].append(key);continue
        local.ack(key,result['record']['revision'],signature)
        count['uploaded']+=1
    report('上传记录',len(keys),len(keys))
    report('正在获取云端目录',0,0)
    meta=local.metadata();by_remote={v['rid']:(k,v) for k,v in meta.items()}
    records=list(remote.list())
    for index,record in enumerate(records):
        report('接收记录与照片',index,len(records))
        if not record['deleted']:count['cloud_records']+=1
        known=by_remote.get(record['id'])
        if known:
            key,old=known
            if record['revision']<=old['revision']:continue
            current=local.snapshots().get(key)
            if digest(current)!=old['hash']:
                if key not in count['conflicts']:count['conflicts'].append(key)
                continue
        else:key=None;old=None;current=None
        try:
            data=None if record['deleted'] else remote.materialize(record['data'])
            if local.apply(key,record,data,digest(current)):
                count['downloaded']+=1
            elif key not in count['conflicts']:count['conflicts'].append(key)
        except (CloudError,OSError,ValueError) as exc:
            count['failures'].append({'key':key or (record['kind'],record['id']),'reason':str(exc) if isinstance(exc,CloudError) else '记录或图片接收失败，请重试'})
    report('同步检查完成',len(records),len(records))
    return count
