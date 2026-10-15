"""Inspect the actual Windows shell properties of a running Flet window."""
import ctypes
from flet_desktop import win_taskbar as shell

def read_identity(hwnd):
    shell._ole32.CoInitialize(None)
    iid=shell.GUID(shell._IID_IPropertyStore)
    ptr=ctypes.c_void_p()
    shell._shell32.SHGetPropertyStoreForWindow(hwnd,ctypes.byref(iid),ctypes.byref(ptr))
    store=ctypes.cast(ptr,ctypes.POINTER(shell.IPropertyStore))
    vtable=store.contents.lpVtbl.contents
    get_value=ctypes.WINFUNCTYPE(ctypes.HRESULT,ctypes.c_void_p,
        ctypes.POINTER(shell.PROPERTYKEY),ctypes.POINTER(shell.PROPVARIANT))(vtable.GetValue)
    result={}
    try:
        for key_id,name in [(2,'command'),(3,'icon'),(4,'name'),(5,'id')]:
            key=shell.PROPERTYKEY()
            key.fmtid=shell.GUID(shell._PKEY_FMTID)
            key.pid=key_id
            value=shell.PROPVARIANT()
            get_value(ptr,ctypes.byref(key),ctypes.byref(value))
            result[name]=ctypes.wstring_at(value.data) if value.vt==31 and value.data else None
            shell._ole32.PropVariantClear(ctypes.byref(value))
    finally:
        vtable.Release(ptr)
        shell._ole32.CoUninitialize()
    return result
