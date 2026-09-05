Option Explicit

Dim progId, request, targetUrl

If WScript.Arguments.Count <> 1 Then
    WScript.Echo "usage: cscript //nologo fetch-connect.vbs URL"
    WScript.Quit 2
End If

targetUrl = WScript.Arguments(0)

For Each progId In Array("Msxml2.XMLHTTP", "Msxml2.XMLHTTP.6.0")
    On Error Resume Next
    Err.Clear
    Set request = CreateObject(progId)
    If Err.Number <> 0 Then
        WScript.Echo progId & " create_error=" & Hex(Err.Number)
    Else
        request.Open "GET", targetUrl, False
        request.SetRequestHeader "Accept", "*/*"
        request.SetRequestHeader "User-Agent", "sldIM"
        request.Send
        If Err.Number <> 0 Then
            WScript.Echo progId & " send_error=" & Hex(Err.Number)
        Else
            WScript.Echo progId & " status=" & request.Status & " chars=" & Len(request.ResponseText)
            WScript.Echo request.ResponseText
        End If
    End If
    Set request = Nothing
    On Error GoTo 0
Next
