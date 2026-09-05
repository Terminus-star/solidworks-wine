#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <ole2.h>
#include <oleauto.h>
#include <msxml2.h>
#include <cstdio>
#include <vector>

static const IID xml_dom_document2_iid =
    {0x2933bf95, 0x7b36, 0x11d2, {0xb2, 0x0e, 0x00, 0xc0, 0x4f, 0x98, 0x3e, 0x60}};

static bool read_file(const wchar_t *path, std::vector<unsigned char> &bytes)
{
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr,
                              OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    DWORD size = GetFileSize(file, nullptr), read = 0;
    bytes.resize(size);
    BOOL ok = ReadFile(file, bytes.data(), size, &read, nullptr);
    CloseHandle(file);
    return ok && read == size;
}

static void test_stream(const wchar_t *prog_id, const char *label,
                        const std::vector<unsigned char> &bytes, bool rewind)
{
    CLSID clsid;
    IXMLDOMDocument2 *document = nullptr;
    IXMLDOMElement *root = nullptr;
    IStream *stream = nullptr;
    BSTR root_name = nullptr;
    VARIANT source;
    VARIANT_BOOL loaded = VARIANT_FALSE;
    DWORD written = 0;
    HRESULT hr;

    hr = CLSIDFromProgID(prog_id, &clsid);
    if (FAILED(hr)) {
        std::printf("%s/%s CLSIDFromProgID=0x%08lx\n", label,
                    rewind ? "rewound" : "at-eof", (unsigned long)hr);
        return;
    }
    hr = CoCreateInstance(clsid, nullptr, CLSCTX_INPROC_SERVER,
                          xml_dom_document2_iid, reinterpret_cast<void **>(&document));
    if (FAILED(hr)) {
        std::printf("%s/%s CoCreateInstance=0x%08lx\n", label,
                    rewind ? "rewound" : "at-eof", (unsigned long)hr);
        return;
    }

    VARIANT_BOOL async = VARIANT_FALSE;
    document->put_async(async);
    hr = CreateStreamOnHGlobal(nullptr, TRUE, &stream);
    if (SUCCEEDED(hr)) hr = stream->Write(bytes.data(), (ULONG)bytes.size(), &written);
    if (SUCCEEDED(hr) && rewind) {
        LARGE_INTEGER zero = {};
        hr = stream->Seek(zero, STREAM_SEEK_SET, nullptr);
    }

    VariantInit(&source);
    V_VT(&source) = VT_UNKNOWN;
    V_UNKNOWN(&source) = stream;
    if (SUCCEEDED(hr)) hr = document->load(source, &loaded);
    std::printf("%s/%s bytes=%lu load=0x%08lx loaded=%d", label,
                rewind ? "rewound" : "at-eof", (unsigned long)written,
                (unsigned long)hr, loaded);
    if (SUCCEEDED(document->get_documentElement(&root)) && root &&
        SUCCEEDED(root->get_nodeName(&root_name)))
        std::printf(" root_chars=%u", (unsigned int)SysStringLen(root_name));
    std::printf("\n");

    if (root_name) SysFreeString(root_name);
    if (root) root->Release();
    if (stream) stream->Release();
    document->Release();
}

int wmain(int argc, wchar_t **argv)
{
    std::vector<unsigned char> bytes;
    if (argc != 2 || !read_file(argv[1], bytes)) return 2;
    HRESULT hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(hr)) return 3;

    const wchar_t *prog_ids[] = {
        L"Msxml2.DOMDocument", L"Msxml2.DOMDocument.3.0", L"Msxml2.DOMDocument.6.0"
    };
    const char *labels[] = {
        "Msxml2.DOMDocument", "Msxml2.DOMDocument.3.0", "Msxml2.DOMDocument.6.0"
    };
    for (unsigned int i = 0; i < 3; ++i) {
        test_stream(prog_ids[i], labels[i], bytes, false);
        test_stream(prog_ids[i], labels[i], bytes, true);
    }

    CoUninitialize();
    return 0;
}
