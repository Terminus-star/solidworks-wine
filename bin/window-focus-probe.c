#define UNICODE
#define _UNICODE
#include <windows.h>
#include <stdio.h>

static void describe(const char *label, HWND window)
{
    WCHAR class_name[256] = L"";
    WCHAR title[256] = L"";
    RECT rect = {0};

    if (window)
    {
        GetClassNameW(window, class_name, ARRAYSIZE(class_name));
        GetWindowTextW(window, title, ARRAYSIZE(title));
        GetWindowRect(window, &rect);
    }
    wprintf(L"%S=%p class=%ls title=%ls rect=%ld,%ld,%ld,%ld\n", label, window,
            class_name, title, rect.left, rect.top, rect.right, rect.bottom);
}

static BOOL CALLBACK describe_child(HWND window, LPARAM context)
{
    unsigned int *count = (unsigned int *)context;
    if ((*count)++ < 32)
        describe("child", window);
    return TRUE;
}

int wmain(void)
{
    HWND top = FindWindowW(NULL, L"SOLIDWORKS 2026 SP3.2 Installation Manager");
    DWORD thread = top ? GetWindowThreadProcessId(top, NULL) : 0;
    GUITHREADINFO info = {sizeof(info)};

    describe("foreground", GetForegroundWindow());
    describe("top", top);
    if (thread && GetGUIThreadInfo(thread, &info))
    {
        describe("active", info.hwndActive);
        describe("focus", info.hwndFocus);
        describe("caret", info.hwndCaret);
    }
    if (top)
    {
        unsigned int count = 0;
        EnumChildWindows(top, describe_child, (LPARAM)&count);
        printf("child_count=%u\n", count);
    }
    return top ? 0 : 1;
}
