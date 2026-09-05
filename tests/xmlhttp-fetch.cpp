#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <ole2.h>
#include <oleauto.h>
#include <msxml2.h>
#include <cstdio>

static const IID xmlhttp_request_iid =
    {0xed8c108d, 0x4349, 0x11d2, {0x91, 0xa4, 0x00, 0xc0, 0x4f, 0x79, 0x69, 0xe8}};
static const IID xml_dom_document2_iid =
    {0x2933bf95, 0x7b36, 0x11d2, {0xb2, 0x0e, 0x00, 0xc0, 0x4f, 0x98, 0x3e, 0x60}};

static void run_request(const wchar_t *prog_id, const char *label, const wchar_t *url)
{
    CLSID clsid;
    IXMLHTTPRequest *request = nullptr;
    IDispatch *response_dispatch = nullptr;
    IXMLDOMDocument2 *response_document = nullptr;
    IXMLDOMElement *root = nullptr;
    BSTR method = nullptr, request_url = nullptr, text = nullptr, root_name = nullptr;
    VARIANT empty, async;
    LONG status = 0, ready_state = 0;
    HRESULT hr, open_hr, send_hr, ready_hr, status_hr, text_hr, xml_hr;

    hr = CLSIDFromProgID(prog_id, &clsid);
    if (FAILED(hr)) {
        std::printf("%s CLSIDFromProgID=0x%08lx\n", label, (unsigned long)hr);
        return;
    }
    hr = CoCreateInstance(clsid, nullptr, CLSCTX_INPROC_SERVER, xmlhttp_request_iid,
                          reinterpret_cast<void **>(&request));
    if (FAILED(hr)) {
        std::printf("%s CoCreateInstance=0x%08lx\n", label, (unsigned long)hr);
        return;
    }

    VariantInit(&empty);
    VariantInit(&async);
    V_VT(&async) = VT_BOOL;
    V_BOOL(&async) = VARIANT_FALSE;
    method = SysAllocString(L"GET");
    request_url = SysAllocString(url);
    open_hr = request->open(method, request_url, async, empty, empty);
    send_hr = SUCCEEDED(open_hr) ? request->send(empty) : open_hr;
    ready_hr = request->get_readyState(&ready_state);
    status_hr = request->get_status(&status);
    text_hr = request->get_responseText(&text);
    xml_hr = request->get_responseXML(&response_dispatch);

    std::printf("%s open=0x%08lx send=0x%08lx ready=0x%08lx/%ld status=0x%08lx/%ld text=0x%08lx",
                label, (unsigned long)open_hr, (unsigned long)send_hr,
                (unsigned long)ready_hr, ready_state, (unsigned long)status_hr, status,
                (unsigned long)text_hr);
    if (SUCCEEDED(text_hr) && text)
        std::printf(" text_chars=%u", (unsigned int)SysStringLen(text));

    std::printf(" xml=0x%08lx", (unsigned long)xml_hr);
    if (SUCCEEDED(xml_hr) && response_dispatch &&
        SUCCEEDED(response_dispatch->QueryInterface(xml_dom_document2_iid,
                  reinterpret_cast<void **>(&response_document))) && response_document &&
        SUCCEEDED(response_document->get_documentElement(&root)) && root &&
        SUCCEEDED(root->get_nodeName(&root_name)))
        std::printf(" root_chars=%u", (unsigned int)SysStringLen(root_name));
    std::printf("\n");

    if (root_name) SysFreeString(root_name);
    if (root) root->Release();
    if (response_document) response_document->Release();
    if (response_dispatch) response_dispatch->Release();
    if (text) SysFreeString(text);
    if (request_url) SysFreeString(request_url);
    if (method) SysFreeString(method);
    request->Release();
}

int wmain(int argc, wchar_t **argv)
{
    HRESULT hr;
    if (argc != 2) return 2;
    hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(hr)) return 3;
    run_request(L"Msxml2.XMLHTTP", "Msxml2.XMLHTTP", argv[1]);
    run_request(L"Msxml2.XMLHTTP.3.0", "Msxml2.XMLHTTP.3.0", argv[1]);
    run_request(L"Msxml2.XMLHTTP.6.0", "Msxml2.XMLHTTP.6.0", argv[1]);
    CoUninitialize();
    return 0;
}
