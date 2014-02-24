#!/usr/bin/env python
import struct
import socket, threading, cgi
from base64 import b64encode
from hashlib import sha1
from json import loads as json_decode, dumps as json_encode

def recv_data (client):
  data = client.recv(1024)
  if not data: return None

  length = ord(data[1]) & 127
  p = 2

  if length == 126:
    length = struct.unpack(">H", data[p:p+2])[0]
    p += 2
  elif length == 127:
    length = struct.unpack(">Q", data[p:p+8])[0]
    p += 8

  masks = [ord(byte) for byte in data[p:p+4]]
  p += 4

  decoded = ""

  for char in data[p:p+length]:
    decoded += chr(ord(char) ^ masks[len(decoded) % 4])

  decoded = cgi.escape(decoded)

  try:
    return json_decode(decoded)
  except:
    return decoded

def send_data (client, data):
  if not isinstance(data, basestring):
    data = json_encode(data)

  client.send(chr(129))
  length = len(data)

  if length <= 125:
    client.send(chr(length))
  elif length >= 126 and length <= 65535:
    client.send(chr(126))
    client.send(struct.pack(">H", length))
  else:
    client.send(chr(127))
    client.send(struct.pack(">Q", length))

  return client.send(data)

def parse_headers (data):
  headers = {}
  lines = data.splitlines()

  for l in lines:
    parts = l.split(": ", 1)

    if len(parts) == 2:
      headers[parts[0]] = parts[1]

  headers['code'] = lines[len(lines) - 1]
  return headers

def handshake (client):
  print 'Handshaking...'
  data = client.recv(1024)
  headers = parse_headers(data)

  key = headers['Sec-WebSocket-Key']
  digest = b64encode(sha1(key + magic).hexdigest().decode('hex'))

  response = 'HTTP/1.1 101 Switching Protocols\r\n'
  response += 'Upgrade: websocket\r\n'
  response += 'Connection: Upgrade\r\n'
  response += 'Sec-WebSocket-Accept: %s\r\n\r\n' % digest

  return client.send(response)

def handle (client, addr):
  t = threading.current_thread()
  print 'New Thread: %s' % t.name
  print 'Active Threads: %s' % threading.activeCount()

  handshake(client)
  lock = threading.Lock()

  while 1:
    data = recv_data(client)
    if not data: break

    print 'Message Received From: %s -> %s' % (addr, data)

    lock.acquire()
    send_data(client, data)
    lock.release()

  print 'Client closed:', addr
  client.close()
  t._Thread__stop()
  t._Thread__delete()
  print 'Active Threads: %s' % threading.activeCount()

def start_server ():
  s = socket.socket()
  s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  s.bind(('', 2001))
  s.listen(5)

  while 1:
    conn, addr = s.accept()
    print 'Connection from:', addr

    server = threading.Thread(target = handle, args = (conn, addr))
    server.daemon = True
    server.start()

magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

if __name__ == '__main__': start_server()
