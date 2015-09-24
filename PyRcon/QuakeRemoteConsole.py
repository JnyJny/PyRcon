'''
A Quake-style Remote Console Base Class

XXX Needs more docs

'''

from socket import socket, AF_INET,SOCK_DGRAM,MSG_WAITALL,MSG_PEEK
from select import select
from .Exceptions import NoResponseError

class BaseRemoteConsole(object):
    '''
    XXX Needs more docs
    '''
    _SEQUENCE = 0x00
    _CHUNKSZ = 2048
    _PREFIX_BYTE = 0xff
    _RCON_CMD = 'rcon '
    def __init__(self,password,hostname='localhost',port=28960):
        '''
        :param: password - string password for server
        :param: hostname - string, name or IP address of server
        :param: port     - integer, port number to contact on hostname
        '''
        self.password = password
        self.host = hostname
        self.port = port

    def __repr__(self):
        return '<%s(%s,%s,%s)>' % (self.__class__.__name__,
                                   self.password,
                                   self.host,
                                   self.port)

    @property
    def reply_header(self):
        '''
        Override this property and provide a byte buffer that 
        is prefixed to data returned by the server.
        '''
        return ''

    @property
    def prefix(self):
        '''
        Bytes values prefixing each command sent to the remote
        console. The Quake-style of prefix was four bytes of 0xFF
        followed by the string 'rcon'.  Later derivitives like
        Call of Duty added a sequence byte inbetween the last 0xFF
        and the 'rcon' string.
        '''
        try:
            return self._prefix
        except AttributeError:
            data = [self._PREFIX_BYTE] * 4
            try:
                data.append(self._SEQUENCE)
            except AttributeError:
                pass
            data.extend(map(ord,self._RCON_CMD))
            self._prefix = bytes(data)
        return self._prefix

    @property
    def udp_sock(self):
        '''
        An (AF_INET,SOCK_DGRAM) socket
        '''
        try:
            return self._udp_sock
        except AttributeError:
            self._udp_sock = socket(AF_INET,SOCK_DGRAM)
        return self._udp_sock

    @property
    def address(self):
        '''
        A tuple of (host,port), determines where messages are sent.
        '''
        return (self.host,self.port)
    
    def send(self,message,encoding,timeout,retries):
        '''
        :param: message  - string holding command to send to server
        :param: encoding - string, typically 'utf-8'   XXX necessary?
        :param: timeout  - float value in seconds 
        :param: retries  - integer number of times to timeout before failing

        :return: string server response to client message

        Sends 'message' to the server and waits for a response.

        Longer responses may entail receiving multiple UDP packets to
        collect the entire response.  Changing the timeout duration
        and the retries count will allow callers to find values that
        work for their target server.

        The Quake-style protocol does not have an EOM component, so a
        timeout scheme is used to decide when the response is
        complete.

        If no data is received after (timeout * retries) seconds,
        the NoResponseError exception is raised with message that was
        not acknowledged and the timeout and retries used.

        '''
        
        data = self.prefix + bytes('%s %s'%(self.password,message),encoding)
        
        self.udp_sock.sendto(data,self.address)

        tries = 0
        chunks = []
        while True:
            read_ready,_,_ = select([self.udp_sock],[],[],timeout)
            if self.udp_sock in read_ready:
                data = self.udp_sock.recv(self._CHUNKSZ)
                if  data.startswith(self.reply_header):
                    chunks.append(data[len(self.reply_header):])
                else:
                    raise ValueError(data)
            else:
                tries += 1
                
            if tries > retries:
                break

        if len(chunks) == 0:
            raise NoResponseError(message,timeout,retries)

        text = ''.join([chunk.decode() for chunk in chunks])

        return text
    
    def clean(self,text,strdefs,emptyString=''):
        '''
        :param: text    - string to be 'cleaned'
        :param: strdefs - list of tuples [(start_character,length)..]
        :return: string with substrings defined in strdefs removed

        Elides strings from the target text that start with
        the specified character for the specified length.
        '''
        
        if strdefs is None:
            strdefs = [ ('^',2), ('"',1) ]

        for startToken,slen in strdefs:
            if slen == 1:
                text = text.replace(startToken,emptyString)
            else:
                try:
                    i = text.index(startToken)
                    text = text.replace(text[i:i+slen],emptyString)
                except ValueError:
                    pass
        return text
    
        


