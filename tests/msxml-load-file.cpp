#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <ole2.h>
#include <oleauto.h>
#include <msxml2.h>
#include <cstdio>

static const IID xml_dom_document2_iid =
    {0x2933bf95, 0x7b36, 0x11d2, {0xb2, 0x0e, 0x00, 0xc0, 0x4f, 0x98, 0x3e, 0x60}};

static void test_file(const wchar_t *prog_id, const char *label, const wchar_t *path)
{
    CLSID clsid;
    IXMLDOMDocument2 *document = nullptr;
    IXMLDOMElement *root = nullptr;
    BSTR root_name = nullptr;
    VARIANT source;
    VARIANT_BOOL loaded = VARIANT_FALSE;
    HRESULT hr;

    hr = CLSIDFromProgID(prog_id, &clsid);
    if (FAILED(hr)) {
        printf("%s CLSIDFromProgID=0x%08lx\n", label, (unsigned long)hr);
        return;
    }
    hr = CoCreateInstance(clsid, nullptr, CLSCTX_INPROC_SERVER,
                          xml_dom_document2_iid, reinterpret_cast<void **>(&document));
    if (FAILED(hr)) {
        printf("%s CoCreateInstance=0x%08lx\n", label, (unsigned long)hr);
        return;
    }

    VariantInit(&source);
    V_VT(&source) = VT_BSTR;
    V_BSTR(&source) = SysAllocString(path);
    hr = document->load(source, &loaded);
    printf("%s load=0x%08lx loaded=%d", label, (unsigned long)hr, loaded);
    if (SUCCEEDED(document->get_documentElement(&root)) && root &&
        SUCCEEDED(root->get_nodeName(&root_name)))
        printf(" root_chars=%u", (unsigned int)SysStringLen(root_name));
    printf("\n");

    if (root_name) SysFreeString(root_name);
    if (root) root->Release();
    VariantClear(&source);
    document->Release();
}

int wmain(int argc, wchar_t **argv)
{
    HRESULT hr;
    if (argc != 2) return 2;
    hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(hr)) return 3;
    test_file(L"Msxml2.DOMDocument", "Msxml2.DOMDocument", argv[1]);
    test_file(L"Msxml2.DOMDocument.3.0", "Msxml2.DOMDocument.3.0", argv[1]);
    test_file(L"Msxml2.DOMDocument.6.0", "Msxml2.DOMDocument.6.0", argv[1]);
    CoUninitialize();
    return 0;
}
