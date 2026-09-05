#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

struct font_check {
    const wchar_t *family;
    unsigned matches;
};

static int CALLBACK check_font(const LOGFONTW *font, const TEXTMETRICW *metrics,
                               DWORD type, LPARAM context)
{
    struct font_check *check = (struct font_check *)context;
    (void)metrics;
    (void)type;
    if (!_wcsicmp(font->lfFaceName, check->family)) check->matches++;
    return 1;
}

int wmain(int argc, wchar_t **argv)
{
    struct font_check check = {argc > 1 ? argv[1] : L"Segoe UI", 0};
    LOGFONTW filter = {0};
    HDC dc = CreateCompatibleDC(NULL);
    HFONT font;
    HGDIOBJ previous;
    wchar_t face[LF_FACESIZE] = {0};
    unsigned named_matches;
    if (!dc) return 2;

    /* SOLIDWORKS must see the requested name in enumeration, not merely
       receive a silent GDI fallback when CreateFont succeeds. */
    filter.lfCharSet = DEFAULT_CHARSET;
    EnumFontFamiliesExW(dc, &filter, check_font, (LPARAM)&check, 0);
    wprintf(L"%ls: all-family enumeration matches=%u\n", check.family, check.matches);
    if (!check.matches) {
        DeleteDC(dc);
        return 1;
    }

    check.matches = 0;
    lstrcpynW(filter.lfFaceName, check.family, LF_FACESIZE);
    EnumFontFamiliesExW(dc, &filter, check_font, (LPARAM)&check, 0);
    named_matches = check.matches;
    filter.lfHeight = -16;
    font = CreateFontIndirectW(&filter);
    if (!font) {
        DeleteDC(dc);
        return 2;
    }
    previous = SelectObject(dc, font);
    GetTextFaceW(dc, LF_FACESIZE, face);
    wprintf(L"%ls: named enumeration matches=%u, selected face=%ls\n",
            check.family, named_matches, face);
    SelectObject(dc, previous);
    DeleteObject(font);
    DeleteDC(dc);
    return named_matches && !_wcsicmp(face, check.family) ? 0 : 1;
}
