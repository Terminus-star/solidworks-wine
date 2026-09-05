#define UNICODE
#define _UNICODE
#include <windows.h>

static HWND render_window;

static BOOL send_virtual_key(WORD virtual_key, DWORD flags)
{
    INPUT input;

    ZeroMemory(&input, sizeof(input));
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = virtual_key;
    input.ki.dwFlags = flags;
    return SendInput(1, &input, sizeof(input)) == 1;
}

static int is_allowed_input(char value)
{
    return (value >= '0' && value <= '9') ||
           (value >= 'A' && value <= 'Z') ||
           (value >= 'a' && value <= 'z') ||
           value == '\b';
}

static BOOL CALLBACK find_render_window(HWND window, LPARAM context)
{
    WCHAR class_name[64];

    (void)context;
    if (GetClassNameW(window, class_name, ARRAYSIZE(class_name)) &&
        !lstrcmpW(class_name, L"Chrome_RenderWidgetHostHWND"))
    {
        render_window = window;
        return FALSE;
    }
    return TRUE;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, WCHAR *command_line, int show)
{
    char buffer[64];
    DWORD received = 0;
    DWORD length;
    DWORD index;
    HWND manager;
    DWORD manager_thread;
    DWORD current_thread;

    (void)instance;
    (void)previous;
    (void)command_line;
    (void)show;

    if (!ReadFile(GetStdHandle(STD_INPUT_HANDLE), buffer, sizeof(buffer), &received, NULL))
        return 2;

    length = received;
    while (length && (buffer[length - 1] == '\r' || buffer[length - 1] == '\n'))
        length--;
    if (!length || length > 24)
        return 3;
    for (index = 0; index < length; index++)
        if (!is_allowed_input(buffer[index]))
            return 4;

    manager = FindWindowW(NULL, L"SOLIDWORKS 2026 SP3.2 Installation Manager");
    if (!manager)
        return 5;
    EnumChildWindows(manager, find_render_window, 0);
    if (!render_window)
        return 6;

    manager_thread = GetWindowThreadProcessId(manager, NULL);
    current_thread = GetCurrentThreadId();
    AttachThreadInput(current_thread, manager_thread, TRUE);
    SetForegroundWindow(manager);
    SetFocus(render_window);
    Sleep(250);

    if (!send_virtual_key(VK_CONTROL, 0) ||
        !send_virtual_key('A', 0) ||
        !send_virtual_key('A', KEYEVENTF_KEYUP) ||
        !send_virtual_key(VK_CONTROL, KEYEVENTF_KEYUP))
        return 7;
    Sleep(100);

    for (index = 0; index < length; index++)
    {
        WCHAR value = (WCHAR)(unsigned char)buffer[index];
        SHORT mapped = value == '\b' ? VK_BACK : VkKeyScanW(value);
        UINT virtual_key;
        BOOL shift;

        if (mapped == -1)
            return 8;
        virtual_key = LOBYTE(mapped);
        shift = (HIBYTE(mapped) & 1) != 0;
        if (shift && !send_virtual_key(VK_SHIFT, 0))
            return 9;
        PostMessageW(render_window, WM_KEYDOWN, virtual_key,
                     1 | ((LPARAM)MapVirtualKeyW(virtual_key, MAPVK_VK_TO_VSC) << 16));
        PostMessageW(render_window, WM_KEYUP, virtual_key,
                     1 | ((LPARAM)MapVirtualKeyW(virtual_key, MAPVK_VK_TO_VSC) << 16) |
                     (1u << 30) | (1u << 31));
        if (shift && !send_virtual_key(VK_SHIFT, KEYEVENTF_KEYUP))
            return 10;
        Sleep(40);
    }

    AttachThreadInput(current_thread, manager_thread, FALSE);
    SecureZeroMemory(buffer, sizeof(buffer));
    return 0;
}
