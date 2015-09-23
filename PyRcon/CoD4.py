from . import RemoteConsole
from .Exceptions import *
from time import sleep

class CoD4RemoteConsole(RemoteConsole):
    _SEQUENCE=0x06
    _CHUNKSZ=4096
    _maps = { 'mp_convoy':'Ambush',
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

    def send(self,message,encoding='utf-8',timeout=0.05,retries=2):
        '''
        Send a message to the remote console. 

        Raises UsageError if the strings 'usage:' or 'unknown command'
        are present in the data returend from the remote console.
        '''

        text = super(CoD4RemoteConsole,self).send(message,
                                                  encoding,
                                                  timeout,
                                                  retries)
        
        lctext = text[:32].lower()

        if lctext.count('usage:'):
            raise UsageError(message,text)

        if lctext.count('unknown command'):
            raise UsageError(message,text)

        return text

    def _list(self,cmd,filterfunc=None):
        '''
        '''
        if filterfunc is None:
            filterfunc = lambda x: len(x)
        return [x for x in self.send(cmd).split('\n') if filterfunc(x)]
        
    @property
    def bindlist(self):
        l = {}
        for pair in self._list('bindlist'):
            if len(pair) == 0:
                continue
            key,val = pair.split(maxsplit=1)
            l.setdefault(key,val.replace('"',''))
        return l
    
    @property
    def channels(self):
        return self._list('con_channellist')

    @property
    def visible_channels(self):
        return self._list('con_visiblechannellist')
    
    @property
    def cmdlist(self):
        cmds = self._list('cmdlist')[:-1]
        cmds.sort()
        return cmds

    @property
    def dvarlist(self):
        dvars = []
        for line in self._list('dvarlist')[:-1]:
            name,_,value = line.partition('"')
            dvars.append(name.split()[-1])
        return dvars
    
    @property
    def fullpath(self):
        return self.send('fullpath')

    @property
    def meminfo(self):
        return self.send('meminfo')

    @property
    def net_dumpprofile(self):
        return self.send('net_dumpprofile')

    @property
    def language(self):
        text = self._list('path')
        return text[0].split()[-1]

    @property
    def fileHandles(self):
        fh = []
        for line in self._list('path'):
            if line.startswith('handle'):
                fh.append(line.split()[-1])
        return fh
    
    @property
    def path(self):
        p = []
        for line in self._list('path'):
            if line.startswith('/'):
                p.append(line.partition('(')[0])
        return p
    
    @property
    def players(self):
        status = self._list('status')
        if len(status) < 3:
            return {}
        players = {}
        labels = status[1].split()
        nameidx = labels.index('name')
        for line in status[3:]:
            data = line.split()
            data[nameidx] = self.clean(data[nameidx])
            players.setdefault(data[nameidx],dict(zip(labels,data)))
        return players
    
    @property
    def scriptUsage(self):
        return self.send('scriptUsage')
        
    @property
    def serverinfo(self):
        d = {}
        for entry in self._list('serverinfo')[1:]:
            fields = entry.split(maxsplit=1)
            if len(fields) == 1:
                # fix up for long names butting into the value
                k = fields[0][:-1]
                v = fields[0][-1]
            else:
                k,v = fields
            d.setdefault(k,v)
        return d
    
    @property
    def status(self):
        return self.send('status')

    @property
    def systeminfo(self):
        dvars = self.dvardump()
        sleep(0.5)
        d = {}
        for entry in self._list('systeminfo')[1:]:
            target = entry.split(maxsplit=1)[0]
            for key,value in dvars.items():
                if target.startswith(key):
                    d.setdefault(key,value)
                    break
        return d
                                  

    ## read/write properties

    @property
    def mapname(self):
        return self.clean(self.send('status').split()[1])

    @mapname.setter
    def mapname(self,mapname):
        self.map(mapname)
        
    ## methods with arguments

    def banClient(self,slotNumber):
        results = self.send('banclient %s' %(slotNumber))
        if results.lower().count('bad slot'):
            return False
        if results.count('not active'):
            return False
        return True

    def banUser(self,user):
        results = self.send('banuser %s' % (user))
        if results.count('not on the server'):
            return False
        return True

    def bind(self,key,command=''):
        '''
        Bind a command to a keyboard key.
        Returns the current binding if command is empty
        '''
        message = 'bind %s %s' % (key,command)
        result = self.send(message)
        if result.count('valid key'):
            raise UsageError(message,result)
        if result.count('='):
            key,cmd = self.clean(result).split('=')
            return {key.strip():cmd.strip()}

    def channel(self,channel,hide=False):
        cmd = { True:'con_hidechannel',False:'con_showchannel'}[hide]
        results = self.send('%s %s' % (cmd,channel))

    def chatmode(self,mode='team'):
        self.send('chatmode%s'%(mode))
        
    def clientkick(self,client):
        result = self.send('clientkick %s' % (client))

    def dir(self,path='.',ext=''):
        if ('*' in path) or ('?' in path):
            files = self._list('fdir %s' %(path))
            del(files[0])
            del(files[-1])
        else:
            files = self._list('dir %s %s' % (path,ext))
            del(files[0:2])
        return files

    def dumpuser(self,user):
        results = self._list('dumpuser %s' %(user))
        if results[0].lower().count('not on the server'):
            raise PlayerNotFound(user)
        
        d = {}
        for pair in results[2:]:
            key,value = pair.split()
            d.setdefault(key,value)
        return d

    def dvardump(self,name=''):
        good = lambda t: len(t) and '==' not in t
        dlist = self._list('dvardump %s' % name,good)
        total = int(dlist[-2].split()[0])
        dvars = {}
        for data in dlist[:-2]:
            key,rawvalue = data.split(maxsplit=1)
            dvars.setdefault(key,self.clean(rawvalue))
        return dvars

    def dvar_int(self,name,value,minimum,maximum):
        msg = 'dvar_int %s %s %s %s'
        msg %= (name,value,minimum,maximum)
        result = self.send(msg)

    def dvar_float(self,name,value,minimum,maximum):
        msg = 'dvar_float %s %s %s %s'
        msg %= (name,value,minimum,maximum)
        result = self.send(msg)

    def dvar_bool(self,name,value):
        result = self.send('dvar_bool %s' % (value))
            
    def execute(self,filename):
        results = self.send('exec %s' % (filename))

    def gamecomplete(self):
        results = self.send('gamecompletestatus')

    def gametype(self,gtype='',restart=False):
        
        result = self.send('g_gametype %s' % (gtype))
        
        if len(gtype) and restart:
            self.restart(fast=False)

        results = result.split()
        
        d = {}
        for phrase in [ 'is:','default:','latched:']:
            try:
                value = self.clean(results[results.index(phrase)+1])
                d.setdefault(phrase[:-1],value)
            except ValueError:
                pass

        return d
    
    def heartbeat(self):
        results = self.send('heartbeat')
        
    def map(self,mapname,cheats=False):
        '''
        Start a map with cheats disabled/enabled.
        '''
        cmd = {True:'devmap',False:'map'}[cheats]
        results = self.send('%s %s' % (cmd,mapname),timeout=0.25,retries=3)
        if results[-3].count('Error'):
            raise FileNotFound(mapname)

    def net_restart(self):
        result = self.send('net_restart')

    def onlykick(self,player):
        result = self.send('onlykick %s' % (player))

    def quit(self,really=False):
        '''
        remote server will quit, not client
        '''
        if really:
            result = self.send('quit')

    # missing all the ragdoll commands

    def say(self,message):
        result = self.send('say %s' % message)

    def tell(self,who,message):
        result = self.send('tell %s %s' % (who,message))

    def set(self,name,value):
        return self.send('set %s %s' % (name,value))

    def seta(self,name,value):
        return self.send('seta %s %s' % (name,value))

    def next_map(self):
        result = self.send('map_rotate')

    def kick(self,player):
        result = self.send('kick %s' % player)

    def killserver(self):
        result = self.send('killserver')

    def restart(self,fast=False):
        if fast:
            result = self.send('fast_restart')
        else:
            result = self.send('map_restart',timeout=0.25)

    def reset(self,dvarname):
        pass

    def resetStats(self):
        results = self.send('resetStats')

    def selectStringTableEntryInDvar(self,index):
        pass

    def set(self,name,value):
        '''
        set value of an existing variable
        '''
        results = self.send('set %s %s' %(cmd,name,value))

    def seta(self,name,value):
        '''
        create a new variable and set it's value
        '''
        results = self.send('seta %s %s' %(cmd,name,value))

    def setu(self,name,value):
        '''
        set a variable for a user
        '''
        results = self.send('setu %s %s' %(cmd,name,value))

    def sets(self,name,value):
        '''
        set a variable for the server
        '''
        results = self.send('set %s %s' %(cmd,name,value))        

    def setPerk(self,user,perk):
        results = self.send('setPerk %s %s' %(user,perk))

    def setDvarToTime(self,dvarname):
        results = self.send('setdvartotime %s' %(dvarname))

    def setfromdvar(self,name,dvarname):
        results = self.send('setfromdvar %s %s' %(name,dvarname))

    def setfromlocstring(self,name,string):
        '''
        localized string getter 
        '''
        result = self.send('setfromlocstring %s %s' %(name,string))

    def statGetInDvar(self,index,dvarname):
        return self.send('statgetindvar %s %s' % (index,dvarname))

    def statSet(self,index,value):
        results = self.send('statSet %s %s' % (index,value))

    def tempBanClient(self,clientNumber):
        results = self.send('tempBanClient %s' % (clientNumber))

    def tempBanUser(self,user):
        results = self.send('tempBanUser %s' % (user))

    def timedemo(self):
        pass

    def toggle(self,name):
        results = self.send('toggle %s' % (name))
        
    def togglep(self,name,optionals=''):
        results = self.send('togglep %s %s' %(name,optionals))
        
    def toggleMenu(self):
        results = self.send('toggleMenu')

    def touchFile(self):
        pass

    def unbanUser(self,user):
        results = self.send('unbanUser %s' % (user))

    def unbind(self,key=None):
        if key is None:
            results = self.send('unbindall')
        else:
            results = self.send('unbind %s' %(key))

    def unskippableCinematic(self):
        pass

    def uploadStats(self):
        pass

    def vstr(self,string):
        results =self.send('vstr %s' % (string))

    def wait(self):
        pass

    def writeConfig(self,filename,defaults=False):
        '''
        writes out a user configuration file
        ~/Library/Application Support/Call of Duty 4/players/<filename>
        '''
        results = self.send('writeconfig %s' % (filename))
        
    def writeDefaults(self,filename):
        '''
        writes out a server configuration file
        ~/Library/Application Support/Call of Duty 4/main/<filename>
        '''
        results = self.send('writedefaults %s' % (filename))
        

host = '75.108.162.152'

r = CoD4RemoteConsole('foobar')

