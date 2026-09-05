#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <msi.h>
#include <msiquery.h>
#include <stdio.h>
#include <wchar.h>

/* The 32-bit helper deliberately uses the project's patched 32-bit MSI host.
 * Credentials enter through stdin, never through the process command line. */
static int query(const wchar_t *path, const wchar_t *sql)
{
    MSIHANDLE db = 0, view = 0, row = 0;
    UINT rc = MsiOpenDatabaseW(path, MSIDBOPEN_READONLY, &db);
    if (!rc) rc = MsiDatabaseOpenViewW(db, sql, &view);
    if (!rc) rc = MsiViewExecute(view, 0);
    while (!rc && (rc = MsiViewFetch(view, &row)) == ERROR_SUCCESS) {
        UINT columns = MsiRecordGetFieldCount(row);
        for (UINT i = 1; i <= columns; i++) {
            wchar_t value[8192];
            DWORD size = sizeof(value) / sizeof(*value);
            UINT field_rc = MsiRecordGetStringW(row, i, value, &size);
            if (field_rc) { rc = field_rc; break; }
            wprintf(L"%ls%ls", i == 1 ? L"" : L"\t", value);
        }
        wprintf(L"\n");
        MsiCloseHandle(row);
        row = 0;
    }
    if (row) MsiCloseHandle(row);
    if (view) MsiCloseHandle(view);
    if (db) MsiCloseHandle(db);
    if (rc == ERROR_NO_MORE_ITEMS) rc = ERROR_SUCCESS;
    if (rc) fwprintf(stderr, L"MSI query failed: %u\n", rc);
    return rc ? 1 : 0;
}

static int verify(int argc, wchar_t **argv)
{
    INSTALLSTATE product = MsiQueryProductStateW(argv[2]);
    int valid = product == INSTALLSTATE_DEFAULT;
    wprintf(L"product\t%d\n", product);
    for (int i = 3; i < argc; i++) {
        INSTALLSTATE feature = MsiQueryFeatureStateW(argv[2], argv[i]);
        wprintf(L"%ls\t%d\n", argv[i], feature);
        if (feature != INSTALLSTATE_LOCAL) valid = 0;
    }
    return valid ? 0 : 1;
}

static int components(int argc, wchar_t **argv)
{
    for (int i = 3; i < argc; ++i) {
        wchar_t path[32768];
        DWORD length = sizeof(path) / sizeof(*path);
        path[0] = 0;
        INSTALLSTATE state = MsiGetComponentPathW(argv[2], argv[i], path, &length);
        wprintf(L"%ls\t%d\t%ls\n", argv[i], state, path);
    }
    return 0;
}

static int install(int argc, wchar_t **argv, int licensed_core)
{
    char serial[128];
    wchar_t properties[16384];
    size_t n;
    if (argc != 5) return 2;
    if (!licensed_core) {
        if (wcslen(argv[4]) >= 16384) return 2;
        wcscpy(properties, argv[4]);
        goto install_package;
    }
    if (!fgets(serial, sizeof(serial), stdin)) return 2;
    n = strcspn(serial, "\r\n");
    serial[n] = 0;
    if (n != 24) return 2;
    for (size_t i = 0; i < n; i++) {
        if ((i < 16 && (serial[i] < '0' || serial[i] > '9')) ||
            (i >= 16 && !(serial[i] >= '0' && serial[i] <= '9') &&
             !(serial[i] >= 'A' && serial[i] <= 'Z'))) return 2;
    }
    int length = swprintf(properties, 16384,
        L"%ls SOLIDWORKSSERIALNUMBER=\"%hs\" MsiHiddenProperties=\"SOLIDWORKSSERIALNUMBER\"",
        argv[4], serial);
    SecureZeroMemory(serial, sizeof(serial));
    if (length < 0 || length >= 16384) return 2;
install_package:
    MsiSetInternalUI(INSTALLUILEVEL_BASIC, NULL);
    UINT rc = MsiEnableLogW(INSTALLLOGMODE_FATALEXIT | INSTALLLOGMODE_ERROR |
        INSTALLLOGMODE_WARNING | INSTALLLOGMODE_USER | INSTALLLOGMODE_INFO |
        INSTALLLOGMODE_RESOLVESOURCE | INSTALLLOGMODE_OUTOFDISKSPACE |
        INSTALLLOGMODE_ACTIONSTART | INSTALLLOGMODE_ACTIONDATA |
        INSTALLLOGMODE_COMMONDATA | INSTALLLOGMODE_PROPERTYDUMP,
        argv[3], INSTALLLOGATTRIBUTES_FLUSHEACHLINE);
    if (!rc) rc = MsiInstallProductW(argv[2], properties);
    SecureZeroMemory(properties, sizeof(properties));
    wprintf(L"MSI_RESULT=%u\n", rc);
    /* Windows success-with-reboot-required does not survive an 8-bit POSIX
     * exit status. The controller records the full result printed above. */
    return (rc == ERROR_SUCCESS || rc == ERROR_SUCCESS_REBOOT_REQUIRED) ? 0 : 1;
}

int wmain(int argc, wchar_t **argv)
{
    if (argc == 4 && !wcscmp(argv[1], L"query")) return query(argv[2], argv[3]);
    if (argc >= 3 && !wcscmp(argv[1], L"verify")) return verify(argc, argv);
    if (argc >= 3 && !wcscmp(argv[1], L"components")) return components(argc, argv);
    if (argc >= 2 && !wcscmp(argv[1], L"install")) return install(argc, argv, 1);
    if (argc >= 2 && !wcscmp(argv[1], L"install-prerequisite")) return install(argc, argv, 0);
    fwprintf(stderr, L"Usage: msi-tool query PACKAGE SQL | verify PRODUCT [FEATURE...] | install PACKAGE LOG PROPERTIES\n");
    return 2;
}
