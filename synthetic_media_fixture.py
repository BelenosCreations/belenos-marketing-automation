"""Small structurally valid PNG fixture for offline tests only.

No actual customer artwork, files, uploads, network or publishing activity.
"""
import struct
import zlib

def _chunk(kind,payload):
    return (struct.pack('>I',len(payload))+kind+payload+
            struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff))

PNG=(b'\x89PNG\r\n\x1a\n'+
     _chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+
     _chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00\xff'))+
     _chunk(b'IEND',b''))
