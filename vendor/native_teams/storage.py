"""Static no-symlink containment around unchanged native VFS; not a hostile-UID sandbox."""
from pathlib import Path
from vendor.native_vfs.store import VFSStore
class StorageDenied(ValueError):pass

def contained(root,path):
    root=Path(root);path=Path(path)
    try:parts=path.relative_to(root).parts
    except ValueError:raise StorageDenied('storage outside owner root')
    if '..' in parts:raise StorageDenied('storage traversal')
    cursor=root
    if cursor.is_symlink():raise StorageDenied('root symlink')
    for part in parts:
        cursor=cursor/part
        if cursor.is_symlink():raise StorageDenied('storage symlink: '+part)
    return path

def sqlite_paths(root,path):
    for suffix in ['', '-wal','-shm','-journal']:contained(root,Path(str(path)+suffix))

class ScopedVFSStore(VFSStore):
    def __init__(self,owner_root,root):
        self.owner_root=Path(owner_root)
        root=contained(self.owner_root,Path(root));contained(self.owner_root,root/'objects');sqlite_paths(self.owner_root,root/'vfs.sqlite3')
        super().__init__(root)
    def _connect(self):
        contained(self.owner_root,self.root);sqlite_paths(self.owner_root,self.db_path)
        return super()._connect()
    def _object_path(self,digest):
        return contained(self.owner_root,super()._object_path(digest))
