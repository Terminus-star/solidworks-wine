#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wininet.h>
#include <stdio.h>

int wmain(int argc, wchar_t **argv)
{
    HINTERNET session, request;
    DWORD status = 0, status_size = sizeof(status), bytes_read, available = 0, query_error;
    BOOL query_result;
    char buffer[4096];
    size_t total = 0;

    if (argc != 2)
    {
        fwprintf(stderr, L"usage: wininet-fetch.exe URL\n");
        return 2;
    }

    session = InternetOpenW(L"sldIM", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
    if (!session)
    {
        fprintf(stderr, "InternetOpenW failed: %lu\n", GetLastError());
        return 3;
    }

    request = InternetOpenUrlW(session, argv[1], L"Accept: */*\r\n", (DWORD)-1,
                               INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!request)
    {
        fprintf(stderr, "InternetOpenUrlW failed: %lu\n", GetLastError());
        InternetCloseHandle(session);
        return 4;
    }

    if (HttpQueryInfoW(request, HTTP_QUERY_STATUS_CODE | HTTP_QUERY_FLAG_NUMBER,
                       &status, &status_size, NULL))
        printf("status=%lu\n", status);

    SetLastError(ERROR_SUCCESS);
    query_result = InternetQueryDataAvailable(request, &available, 0, 0);
    query_error = GetLastError();
    printf("query_available=%d available=%lu error=%lu\n",
           query_result, available, query_error);

    while (InternetReadFile(request, buffer, sizeof(buffer), &bytes_read) && bytes_read)
    {
        fwrite(buffer, 1, bytes_read, stdout);
        total += bytes_read;
    }

    printf("\nbytes=%zu error=%lu\n", total, GetLastError());
    InternetCloseHandle(request);
    InternetCloseHandle(session);
    return total ? 0 : 5;
}
