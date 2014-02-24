#!/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/python
import struct
import socket, threading, cgi
from base64 import b64encode
from hashlib import sha1
from json import loads as json_decode, dumps as json_encode
import sys, os, time, atexit
from signal import SIGTERM

class Daemon:
  """
  A generic daemon class.

  Usage: subclass the Daemon class and override the run() method
  """
  def __init__(self, pidfile, stdin='/dev/null', stdout='/var/log/serverSocket.log', stderr='/var/log/serverSocket.error.log'):
      self.stdin = stdin
      self.stdout = stdout
      self.stderr = stderr
      self.pidfile = pidfile

  def daemonize(self):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """
    try:
      pid = os.fork()
      if pid > 0:
        # exit first parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
      pid = os.fork()
      if pid > 0:
        # exit from second parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file(self.stdin, 'r')
    so = file(self.stdout, 'a+')
    se = file(self.stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # write pidfile
    atexit.register(self.delpid)
    pid = str(os.getpid())
    file(self.pidfile,'w+').write("%s\n" % pid)

  def delpid(self):
    os.remove(self.pidfile)

  def start(self):
    """
    Start the daemon
    """
    # Check for a pidfile to see if the daemon already runs
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None

    if pid:
      message = "pidfile %s already exist. Daemon already running?\n"
      sys.stderr.write(message % self.pidfile)
      sys.exit(1)

    # Start the daemon
    self.daemonize()
    self.run()

  def stop(self):
    """
    Stop the daemon
    """
    # Get the pid from the pidfile
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None

    if not pid:
      message = "pidfile %s does not exist. Daemon not running?\n"
      sys.stderr.write(message % self.pidfile)
      return # not an error in a restart

    # Try killing the daemon process
    try:
      while 1:
        os.kill(pid, SIGTERM)
        time.sleep(0.1)
    except OSError, err:
      err = str(err)
      if err.find("No such process") > 0:
        if os.path.exists(self.pidfile):
          os.remove(self.pidfile)
      else:
        print str(err)
        sys.exit(1)

  def restart(self):
    """
    Restart the daemon
    """
    self.stop()
    self.start()

  def run(self):
    """
    You should override this method when you subclass Daemon. It will be called after the process has been
    daemonized by start() or restart().
        """


class SocketDaemon(Daemon):

  def recv_data (self,client):
      data = client.recv(1024)
      return json_decode(data)

  def send_data (self,client, data):
      data = json_encode(data)
      return client.send(data)

  def handshake (self,client):
      print 'Handshaking...'
      response = 'You are connected to Chaz serverSocket!!'
      return client.send(response)

  def handle (self,client, addr):
    t = threading.current_thread()
    print 'New Thread: %s' % t.name
    print 'Active Threads: %s' % threading.activeCount()

    self.handshake(client)
    lock = threading.Lock()

    while 1:
      data = self.recv_data(client)
      if not data: break

      print 'Message Received From: %s -> %s' % (addr, data)

      lock.acquire()
      self.send_data(client, data)
      lock.release()

    print 'Client closed:', addr
    client.close()
    t._Thread__stop()
    t._Thread__delete()
    print 'Active Threads: %s' % threading.activeCount()

  def run (self):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 6666))
    s.listen(5)

    while 1:
      conn, addr = s.accept()
      print 'Connection from:', addr

      server = threading.Thread(target = self.handle, args = (conn, addr))
      server.daemon = True
      server.start()

magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

if __name__ == "__main__":
  daemon = SocketDaemon('/tmp/daemon-example.pid')
  if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
      daemon.start()
    elif 'stop' == sys.argv[1]:
      daemon.stop()
    elif 'restart' == sys.argv[1]:
      daemon.restart()
    else:
      print "Unknown command"
      sys.exit(2)
    sys.exit(0)
  else:
    print "usage: %s start|stop|restart" % sys.argv[0]
    sys.exit(2)
