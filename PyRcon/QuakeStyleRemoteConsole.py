'''

'''

from socket import socket, AF_INET,SOCK_DGRAM,MSG_WAITALL,MSG_PEEK
from select import select
from .Exceptions import NoResponseError

class RemoteConsole(object):
    _SEQUENCE = 0x00
    _CHUNKSZ = 2048
    
    def __init__(self,password,hostname='localhost',port=28960):
        self.password = password
        self.host = hostname
        self.port = port
        
    def __str__(self):
        return self.status()

    def __repr__(self):
        return '<%s(%s,%s,%s)>' % (self.__class__.__name__,
                                   self.password,
                                   self.hostname,
                                   self.port)

    @property
    def reply_header(self):
        try:
            return self._reply_header
        except AttributeError:
            data = [0xff,0xff,0xff,0xff]
            data.extend(map(lambda c:ord(c),'print\n'))
            self._reply_header = bytes(data)
        return self._reply_header
    
    
    def send(self,message,encoding,timeout,retries):
        '''
        Sends 'message' to the server and waits for a response.
        Longer responses may spawn UDP packets and so may require
        multiple recv() calls. There doesn't seem to be an EOM marker,
        so we wait until there has been a lull in the data sent from the
        server before zortching off the 0xffffffffprint\n from the 
        beginning of each block and concatenating the blocks.
        '''
        
        data = self.prefix + bytes('%s %s'%(self.password,message),encoding)
        
        self.sock.sendto(data,self.address)

        tries = 0
        chunks = []
        while True:
            read_ready,_,_ = select([self.sock],[],[],timeout)
            if self.sock in read_ready:
                data = self.sock.recv(self._CHUNKSZ)

                #print(self._CHUNKSZ,len(data),data[4:20],data[-16:])
                
                if data.startswith(self.reply_header):
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

            
    @property
    def sock(self):
        try:
            return self._sock
        except AttributeError:
            self._sock = socket(AF_INET,SOCK_DGRAM)
        return self._sock

    @property
    def address(self):
        return (self.host,self.port)
    

    def clean(self,text,strdefs=None,emptyString=''):
        '''
        text    : string to be 'cleaned'
        strdefs : a list of tuples (start_character,length) 

        Elides strings from the target text that start with
        the specified character for the specified length.
        
        CoD4 embeds ^# codes in text to specify color choices
        and is over-enthusiastic with it's use of double quotes.

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
    
        
    @property
    def prefix(self):
        '''
        Bytes values prefixing each command sent to the remote
        console. The Quake-style of prefix was four bytes of 0xFF
        followed by the string 'rcon'.  Later derivitives like
        Call of Duty added a sequence byte inbetween the last 0xFF
        and the 'rcon' string. CoD4 will accept sequence values of
        2,6,11 .. mumble .. and 31.  I don't know what it means.
        '''
        try:
            return self._prefix
        except AttributeError:
            # 0xffffffff,0x02rcon\s
            data = [0xff,0xff,0xff,0xff,self._SEQUENCE]
            data.extend(map(ord,'rcon '))
            self._prefix = bytearray(data)
                                 
        return self._prefix

