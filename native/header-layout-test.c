#define UNICODE
#define _UNICODE
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>

int main(void)
{
    INITCOMMONCONTROLSEX init = {sizeof(init), ICC_LISTVIEW_CLASSES};
    RECT rect = {0, 0, 200, 200};
    WINDOWPOS position = {0};
    HDLAYOUT layout = {&rect, &position};
    HWND parent, header;
    if (!InitCommonControlsEx(&init)) return 2;
    parent = CreateWindowW(L"STATIC", L"Header test", WS_OVERLAPPEDWINDOW,
                           0, 0, 200, 200, NULL, NULL, NULL, NULL);
    header = CreateWindowW(WC_HEADERW, L"", WS_CHILD | HDS_HORZ,
                           0, 0, 200, 20, parent, NULL, NULL, NULL);
    if (!header) return 2;
    if (!SendMessageW(header, HDM_LAYOUT, 0, (LPARAM)&layout)) return 1;
    if (position.cx != 200) return 1;
    if (SendMessageW(header, HDM_LAYOUT, 0, 0)) return 1;
    layout.prc = NULL;
    if (SendMessageW(header, HDM_LAYOUT, 0, (LPARAM)&layout)) return 1;
    layout.prc = &rect;
    layout.pwpos = NULL;
    if (SendMessageW(header, HDM_LAYOUT, 0, (LPARAM)&layout)) return 1;
    DestroyWindow(parent);
    puts("Header layout: valid request and all three null cases PASS");
    return 0;
}
