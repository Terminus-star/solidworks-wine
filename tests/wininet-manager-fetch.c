#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wininet.h>
#include <stdio.h>

int wmain(void)
{
    static const wchar_t host[] = L"im.solidworks.com";
    static const wchar_t path[] =
        L"/2026/Connect.aspx?Release=20260-40302-1100-100&Debug=0&ini=1&"
        L"osa=131072:0:2&lid=1033&app=I&cx=1:-1&cm=-1&lfr=&lfp=&lfv=";
    HINTERNET session, connection, request;
    DWORD status = 0, status_size = sizeof(status), bytes_read = 0, second_read = 0, seek;
    DWORD flags = 0xa0600001;
    char buffer[513];
    BOOL ok;

    session = InternetOpenW(L"sldIM", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
    if (!session) return 2;

    connection = InternetConnectW(session, host, INTERNET_DEFAULT_HTTP_PORT,
                                  NULL, NULL, INTERNET_SERVICE_HTTP, 0, 1);
    if (!connection) return 3;

    request = HttpOpenRequestW(connection, L"GET", path, L"HTTP/1.0",
                               NULL, NULL, flags, 1);
    if (!request) return 4;

    ok = HttpAddRequestHeadersW(request, L"Accept: */*\r\nUser-Agent: sldIM\r\n",
                                (DWORD)-1, HTTP_ADDREQ_FLAG_ADD);
    printf("add_headers=%d error=%lu\n", ok, GetLastError());

    ok = HttpSendRequestW(request, NULL, 0, NULL, 0);
    printf("send=%d error=%lu\n", ok, GetLastError());
    if (!ok) return 5;

    if (HttpQueryInfoW(request, HTTP_QUERY_STATUS_CODE | HTTP_QUERY_FLAG_NUMBER,
                       &status, &status_size, NULL))
        printf("status=%lu\n", status);

    SetLastError(ERROR_SUCCESS);
    seek = InternetSetFilePointer(request, 0, NULL, FILE_BEGIN, 0);
    printf("seek=%lu error=%lu\n", seek, GetLastError());

    SetLastError(ERROR_SUCCESS);
    ok = InternetReadFile(request, buffer, 512, &bytes_read);
    printf("read=%d bytes=%lu error=%lu\n", ok, bytes_read, GetLastError());
    if (bytes_read) {
        buffer[bytes_read] = 0;
        fwrite(buffer, 1, bytes_read, stdout);
        putchar('\n');
    }

    SetLastError(ERROR_SUCCESS);
    seek = InternetSetFilePointer(request, 0, NULL, FILE_BEGIN, 0);
    printf("rewind=%lu error=%lu\n", seek, GetLastError());
    SetLastError(ERROR_SUCCESS);
    ok = InternetReadFile(request, buffer, 512, &second_read);
    printf("reread=%d bytes=%lu error=%lu\n", ok, second_read, GetLastError());

    InternetCloseHandle(request);
    InternetCloseHandle(connection);
    InternetCloseHandle(session);
    return bytes_read && second_read == bytes_read ? 0 : 6;
}
