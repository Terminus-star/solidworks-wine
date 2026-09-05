#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <ole2.h>
#include <oleauto.h>
#include <msxml2.h>
#include <cstdio>

static const IID xml_dom_document2_iid =
    {0x2933bf95, 0x7b36, 0x11d2, {0xb2, 0x0e, 0x00, 0xc0, 0x4f, 0x98, 0x3e, 0x60}};

static void test_parser(const wchar_t *prog_id, const char *label)
{
    static const wchar_t xml[] =
        L"<?xml version=\"1.0\" encoding=\"utf-8\"?>\r\n"
        L"<ReleaseInfo xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" "
        L"xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">\r\n"
        L"  <Access>1</Access>\r\n  <Status>0</Status>\r\n</ReleaseInfo>";
    CLSID clsid;
    IXMLDOMDocument2 *document = nullptr;
    IXMLDOMNode *node = nullptr;
    BSTR source = nullptr, query = nullptr, text = nullptr;
    VARIANT_BOOL loaded = VARIANT_FALSE;
    HRESULT hr;

    hr = CLSIDFromProgID(prog_id, &clsid);
    if (FAILED(hr))
    {
        printf("%s CLSIDFromProgID=0x%08lx\n", label, (unsigned long)hr);
        return;
    }

    hr = CoCreateInstance(clsid, nullptr, CLSCTX_INPROC_SERVER,
                          xml_dom_document2_iid, reinterpret_cast<void **>(&document));
    if (FAILED(hr))
    {
        printf("%s CoCreateInstance=0x%08lx\n", label, (unsigned long)hr);
        return;
    }

    source = SysAllocString(xml);
    hr = document->loadXML(source, &loaded);
    printf("%s loadXML=0x%08lx loaded=%d", label, (unsigned long)hr, loaded);
    if (SUCCEEDED(hr) && loaded == VARIANT_TRUE)
    {
        query = SysAllocString(L"/ReleaseInfo/Access");
        hr = document->selectSingleNode(query, &node);
        printf(" select=0x%08lx node=%s", (unsigned long)hr, node ? "yes" : "no");
        if (node && SUCCEEDED(node->get_text(&text)))
            printf(" text_code=%u", (unsigned int)text[0]);
    }
    printf("\n");

    if (text) SysFreeString(text);
    if (query) SysFreeString(query);
    if (source) SysFreeString(source);
    if (node) node->Release();
    document->Release();
}

int wmain()
{
    HRESULT hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(hr)) return 2;
    test_parser(L"Msxml2.DOMDocument", "Msxml2.DOMDocument");
    test_parser(L"Msxml2.DOMDocument.3.0", "Msxml2.DOMDocument.3.0");
    test_parser(L"Msxml2.DOMDocument.6.0", "Msxml2.DOMDocument.6.0");
    CoUninitialize();
    return 0;
}
