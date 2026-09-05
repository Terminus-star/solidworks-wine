#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

static BOOL CALLBACK child(HWND window, LPARAM unused)
{
    wchar_t title[2048], cls[128];
    (void)unused;
    GetClassNameW(window, cls, 128);
    if (!wcsicmp(cls, L"Edit")) wcscpy(title, L"[input redacted]");
    else GetWindowTextW(window, title, 2048);
    if (IsWindowVisible(window))
        wprintf(L"  %p id=%d %ls %ls\n", window, GetDlgCtrlID(window), cls, title);
    return TRUE;
}

static BOOL CALLBACK top(HWND window, LPARAM pid)
{
    DWORD owner;
    wchar_t title[2048];
    GetWindowThreadProcessId(window, &owner);
    if ((pid && owner != (DWORD)pid) || !IsWindowVisible(window)) return TRUE;
    GetWindowTextW(window, title, 2048);
    wprintf(L"%p pid=%lu %ls\n", window, owner, title);
    EnumChildWindows(window, child, 0);
    return TRUE;
}

int wmain(int argc, wchar_t **argv)
{
    if (argc == 3 && !wcscmp(argv[1], L"click")) {
        HWND window = (HWND)(ULONG_PTR)wcstoul(argv[2], NULL, 16);
        DWORD_PTR result;
        return SendMessageTimeoutW(window, BM_CLICK, 0, 0, SMTO_ABORTIFHUNG, 2000, &result) ? 0 : 1;
    }
    if (argc == 3 && !wcscmp(argv[1], L"close")) {
        HWND window = (HWND)(ULONG_PTR)wcstoul(argv[2], NULL, 16);
        return PostMessageW(window, WM_CLOSE, 0, 0) ? 0 : 1;
    }
    EnumWindows(top, argc > 1 ? wcstoul(argv[1], NULL, 10) : 0);
    return 0;
}
