#!/usr/bin/env python3

from socket import *
from select import select

class NoDataReturned(Exception):
    pass

class UsageError(Exception):
    def __init__(self,command,message):
        self.command = command
        self.message = message

    def __str__(self):
        return '%s resulted in %s' % (self.command,self.message)

CoD4Maps = { 'mp_convoy':'Ambush',
             'mp_backlot':'Backlot',
             'mp_bloc':'Bloc',
             'mp_bog':'Bog',
             'mp_countdown':'Countdown',
             'mp_crash':'Crash',
             'mp_crossfire':'Crossfire',
             'mp_citystreets':'District',
             'mp_farm':'Downpour',
             'mp_overgrown':'Overgrown',
             'mp_pipeline':'Pipeline',
             'mp_shipment':'Shipment',
             'mp_showdown':'Showdown',
             'mp_strike':'Strike',
             'mp_vacant':'Vacant',
             'mp_cargoship':'WetWork',
             'mp_crash_snow':'WinterCrash',
             'mp_broadcast':'Broadcast',
             'mp_carentan':'Chinatown',
             'mp_creek':'Creek',
             'mp_killhouse':'Killhouse' }


class rcons(object):
    _SEQ_ = 0x02
    @classmethod
    def scan(cls,password,hostname):
        port = 28900
        found = False
        while not found:
            r = cls(password,hostname,port)
            try:
                if r.verify():
                    return r
            except:
                found = False
            port += 1
            if port > 29000:
                raise ValueError('port is %s' % (port))
        raise ValueError("nobody home")
            
    
    def __init__(self,password,hostname='localhost',port=28960):
        self.password = password
        self.s = socket(AF_INET,SOCK_DGRAM)
        self.hostname = hostname
        self.port = port
        self.s.connect((self.hostname,self.port))

    def __str__(self):
        return self.status()

    def __repr__(self):
        return '<%s(%s,%s,%s)>' % (self.__class__.__name__,
                                   self.password,
                                   self.hostname,
                                   self.port)

    def _send(self,message,encoding='utf-8',timeout=0.05,numberOfRetries=2):
        '''
        Sends 'message' to the server and waits for a response.
        Longer responses may spawn UDP packets and so may require
        multiple recv() calls. There doesn't seem to be an EOM marker,
        so we wait until there has been a lull in the data sent from the
        server before zortching off the 0xffffffffprint\n from the 
        beginning of each block and concatenating the blocks.
        '''
        
        data = self.prefix + bytes('%s %s'%(self.password,message),encoding)
        
        self.s.send(data)

        tries = 0
        blocks = []
        while True:
            r,_,_ = select([self.s],[],[],timeout)
            if len(r):
                blocks.append(self.s.recv(8192))
            else:
                tries += 1
            if tries > numberOfRetries:
                break

        if len(blocks) == 0:
            raise NoDataReturned()
            
        text = ''.join([b[10:].decode() for b in blocks])

        if text.lower().count('usage:') > 0: 
            raise UsageError(message,text)

        # this isn't working.. case sensitive?
        if text.lower().startswith('unknown comand'):
            raise UsageError(message,text)

        return text

    def _clean(self,text,strdefs=None,emptyString=''):
        '''
        This is expensive, don't do use it on large chunks of text.
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
        try:
            return self._prefix
        except AttributeError:
            # 0xffffffff,0x02rcon\s
            self._prefix = bytearray([0xff,0xff,0xff,0xff,self._SEQ_,114,99,111,110,32])
        return self._prefix

    @property
    def bindlist(self):
        results = self._send('bindlist').split('\n')
        l = {}
        for pair in results:
            if len(pair) == 0:
                continue
            key,val = pair.split(maxsplit=1)
            l.setdefault(key,val.replace('"',''))
        return l
    
    @property
    def channels(self):
        return [x for x in self._send('con_channellist').split('\n') if len(x)]

    @property
    def visible_channels(self):
        return [x for x in self._send('con_visiblechannellist').split('\n') if len(x)]

    @property
    def cmds(self):
        try:
            return self._cmds
        except AttributeError:
            tokens = self.cmdlist.split('\n')
            self._cmds = tokens[:-2]
            self._cmds.sort()
        return self._cmds
    
    @property
    def cmdlist(self):
        return self._send('cmdlist')

    @property
    def dvarlist(self):
        return self._send('dvarlist')

    @property
    def dvardump(self):
        return self._send('dvardump')

    @property
    def dvars(self):
        raw = [x for x in self.dvardump.split('\n') if len(x) and '==' not in x]
        total = int(raw[-2].split()[0])
        indices = int(raw[-1].split()[0])
        dvars = {}
        for data in raw[:-2]:
            key,rawvalue = data.split(maxsplit=1)
            dvars.setdefault(key,self._clean(rawvalue))
        return dvars
    
    @property
    def fullpath(self):
        return self._send('fullpath')

    @property
    def meminfo(self):
        return self._send('meminfo')

    @property
    def net_dumpprofile(self):
        return self._send('net_dumpprofile')

    @property
    def path(self):    
        return self._send('path')
    
    @property
    def players(self):
        status = [x for x in self.status.split('\n') if len(x)]
        if len(status) < 3:
            return {}
        players = {}
        labels = status[1].split()
        nameidx = labels.index('name')
        for line in status[3:]:
            data = line.split()
            data[nameidx] = self._clean(data[nameidx])
            players.setdefault(data[nameidx],dict(zip(labels,data)))
        return players
    
    @property
    def scriptUsage(self):
        return self._send('scriptUsage')
        
    @property
    def serverinfo(self):
        return self._send('serverinfo')
    
    @property
    def status(self):
        return self._send('status')

    @property
    def systeminfo(self):
        return self._send('systeminfo')

    ## read/write properties

    @property
    def mapname(self):
        return self._clean(self._send('status').split()[1])

    @mapname.setter
    def mapname(self,mapname):
        self.map(mapname)
        
    ## methods with arguments

    def banClient(self,slotNumber):
        results = self._send('banclient %s' %(slotNumber))
        if results.count('Bad slot'):
            return False
        if results.count('not active'):
            return False
        return True

    def banUser(self,user):
        results = self._send('banuser %s' % (user))
        if results.count('not on the server'):
            return False
        return True

    def bind(self,key,command=''):
        '''
        Bind a command to a keyboard key.
        Returns the current binding if command is empty
        '''
        message = 'bind %s %s' % (key,command)
        result = self._send(message)
        if result.count('valid key'):
            raise UsageError(message,result)
        if result.count('='):
            key,cmd = self._clean(result).split('=')
            return {key.strip():cmd.strip()}

    def channel(self,channel,hide=False):
        cmd = { True:'con_hidechannel',False:'con_showchannel'}[hide]
        results = self._send('%s %s' % (cmd,channel))

    def chatmode(self,team=False):
        results = self._send({True:'chatmodeteam',False:'chatmodepublic'}[team])
        
    def clientkick(self,client):
        result = self._send('clientkick %s' % (client))

    def dir(self,path='.',ext=''):

        if ('*' in path) or ('?' in path):
            files = [x for x in self._send('fdir %s' %(path)).split('\n') if len(x)]
            del(files[0])
            del(files[-1])
        else:
            files = [x for x in self._send('dir %s %s' % (path,ext)).split('\n') if len(x)]
            del(files[0:2])
        return files

    def dumpuser(self,user):
        results = self._send('dumpuser %s' %(user))
        d = {}
        
        if results.count('not on the server'):
            return d
        
        for pair in [x for x in results.split('\n')[2:] if len(x)]:
            key,value = pair.split()
            d.setdefault(key,value)
        return d

    def dvar(self,name,value=None,minimum=0.0,maximum=1.0,isBool=False):

        if value is None:
            result = self._send('dvardump %s' % (name)).split('\n')
            if len(result[1]) == 0:
                raise ValueError('dvar %s not found' %(name))
            return result[1].replace('"','').split()[1].strip()
                    
        cmd = {True:'dvar_float',False:'dvar_int'}[isinstance(value,float)]

        if isBool:
            result = self._send('dvar_bool %s %s' %(cmd,name,value))
        else:
            result = self._send('%s %s %s %s %s' %(cmd,name,value,minimum,maximum))

    def execute(self,filename):
        results = self._send('exec %s' % (filename))

    def gamecomplete(self):
        results = self._send('gamecompletestatus')

    def gametype(self,gtype='',restart=False):
        result = self._send('g_gametype %s' % (gtype))
        
        if gtype != '' and restart:
            self.restart(fast=False)

        results = result.split()
        
        d = {}
        for phrase in [ 'is:','default:','latched:']:
            try:
                value = self._clean(results[results.index(phrase)+1])
                d.setdefault(phrase[:-1],value)
            except ValueError:
                pass

        return d
    
    def heartbeat(self):
        results = self._send('heartbeat')
        
    def map(self,mapname,cheats=False):
        '''
        Start a map with cheats disabled/enabled.
        '''
        cmd = {True:'devmap',False:'map'}[cheats]
        for tries in range(0,2):
            try:
                results = self._send('%s %s' % (cmd,mapname),timeout=0.25)
            except NoDataReturned:
                pass
            else:
                break
        if results[-3].count('Error'):
            raise FileNotFound(mapname)            

    def net_restart(self):
        result = self._send('net_restart')

    def onlykick(self,player):
        result = self._send('onlykick %s' % (player))

    def quit(self,really=False):
        '''
        remote server will quit, not client
        '''
        if really:
            result = self._send('quit')

    # missing all the ragdoll commands

    def say(self,message):
        result = self._send('say %s' % message)

    def tell(self,who,message):
        result = self._send('tell %s %s' % (who,message))

    def set(self,name,value):
        return self._send('set %s %s' % (name,value))

    def seta(self,name,value):
        return self._send('seta %s %s' % (name,value))

    def next_map(self):
        result = self._send('map_rotate')

    def kick(self,player):
        result = self._send('kick %s' % player)

    def killserver(self):
        result = self._send('killserver')

    def restart(self,fast=False):
        if fast:
            result = self._send('fast_restart')
        else:
            result = self._send('map_restart',timeout=0.25)

    def reset(self,dvarname):
        pass

    def resetStats(self):
        results = self._send('resetStats')

    def selectStringTableEntryInDvar(self,index):
        pass

    def set(self,name,value):
        '''
        set value of an existing variable
        '''
        results = self._send('set %s %s' %(cmd,name,value))

    def seta(self,name,value):
        '''
        create a new variable and set it's value
        '''
        results = self._send('seta %s %s' %(cmd,name,value))

    def setu(self,name,value):
        '''
        set a variable for a user
        '''
        results = self._send('setu %s %s' %(cmd,name,value))

    def sets(self,name,value):
        '''
        set a variable for the server
        '''
        results = self._send('set %s %s' %(cmd,name,value))        

    def setPerk(self,user,perk):
        results = self._send('setPerk %s %s' %(user,perk))

    def setDvarToTime(self,dvarname):
        results = self._send('setdvartotime %s' %(dvarname))

    def setfromdvar(self,name,dvarname):
        results = self._send('setfromdvar %s %s' %(name,dvarname))

    def setfromlocstring(self,name,string):
        '''
        localized string getter 
        '''
        result = self._send('setfromlocstring %s %s' %(name,string))

    def statGetInDvar(self,index,dvarname):
        return self._send('statgetindvar %s %s' % (index,dvarname))

    def statSet(self,index,value):
        results = self._send('statSet %s %s' % (index,value))

    def tempBanClient(self,clientNumber):
        results = self._send('tempBanClient %s' % (clientNumber))

    def tempBanUser(self,user):
        results = self._send('tempBanUser %s' % (user))

    def timedemo(self):
        pass

    def toggle(self,name):
        results = self._send('toggle %s' % (name))
        
    def togglep(self,name,optionals=''):
        results = self._send('togglep %s %s' %(name,optionals))
        
    def toggleMenu(self):
        results = self._send('toggleMenu')

    def touchFile(self):
        pass

    def unbanUser(self,user):
        results = self._send('unbanUser %s' % (user))

    def unbind(self,key=None):
        if key is None:
            results = self._send('unbindall')
        else:
            results = self._send('unbind %s' %(key))

    def unskippableCinematic(self):
        pass

    def uploadStats(self):
        pass

    def vstr(self,string):
        results =self._send('vstr %s' % (string))

    def wait(self):
        pass

    def writeConfig(self,filename,defaults=False):
        '''
        writes out a user configuration file
        ~/Library/Application Support/Call of Duty 4/players/<filename>
        '''
        results = self._send('writeconfig %s' % (filename))
        
    def writeDefaults(self,filename):
        '''
        writes out a server configuration file
        ~/Library/Application Support/Call of Duty 4/main/<filename>
        '''
        results = self._send('writedefaults %s' % (filename))
        
    def verify(self):
        try:
            text = self.cmdlist.split('\n')
        except:
            return False
        cmds = text[:-2]
        cnt = int(text[-2].split()[0])
        cmds.sort()
        return len(cmds) == cnt,cmds

host = '75.108.162.152'

r = rcons('foobar')

