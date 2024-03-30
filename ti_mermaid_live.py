import zlib
import base64
import json

def pako_deflate(data):
    compress = zlib.compressobj(9, zlib.DEFLATED, 15, 8, zlib.Z_DEFAULT_STRATEGY)
    compressed_data = compress.compress(data)
    compressed_data += compress.flush()
    return compressed_data


def js_btoa(data):
    return base64.b64encode(data)


def genPakoLink(graphMarkdown: str):
    jGraph = {"code": graphMarkdown, "mermaid": {"theme": "default"}}
    byteStr = json.dumps(jGraph).encode('utf-8')
    deflated = pako_deflate(byteStr)
    dEncode = js_btoa(deflated)
    link = 'http://mermaid.live/edit#pako:' + dEncode.decode('ascii')
    return link
