#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <objbase.h>
#include <stdio.h>

int wmain(int argc, wchar_t **argv)
{
    int failed = 0;
    CoInitialize(NULL);
    for (int i = 1; i < argc; i++) {
        CLSID clsid;
        IUnknown *object = NULL;
        HRESULT result = CLSIDFromProgID(argv[i], &clsid);
        if (SUCCEEDED(result)) result = CoCreateInstance(&clsid, NULL, CLSCTX_INPROC_SERVER | CLSCTX_LOCAL_SERVER,
                                                       &IID_IUnknown, (void **)&object);
        wprintf(L"%ls HRESULT=0x%08lx\n", argv[i], result);
        if (object) object->lpVtbl->Release(object);
        if (FAILED(result)) failed = 1;
    }
    CoUninitialize();
    return failed;
}
