
from .QuakeRemoteConsole import BaseRemoteConsole
from .Exceptions import *
from time import sleep

class RemoteConsole(BaseRemoteConsole):
    '''
    '''
    _SEQUENCE=0x02
    _maps = { 'mp_convoy':     'Ambush',
              'mp_backlot':    'Backlot',
              'mp_bloc':       'Bloc',
              'mp_bog':        'Bog',
              'mp_countdown':  'Countdown',
              'mp_crash':      'Crash',
              'mp_crossfire':  'Crossfire',
              'mp_citystreets':'District',
              'mp_farm':       'Downpour',
              'mp_overgrown':  'Overgrown',
              'mp_pipeline':   'Pipeline',
              'mp_shipment':   'Shipment',
              'mp_showdown':   'Showdown',
              'mp_strike':     'Strike',
              'mp_vacant':     'Vacant',
              'mp_cargoship':  'WetWork',
              'mp_crash_snow': 'WinterCrash',
              'mp_broadcast':  'Broadcast',
              'mp_carentan':   'Chinatown',
              'mp_creek':      'Creek',
              'mp_killhouse':  'Killhouse' }

    def __str__(self):
        return self.status

    @property
    def reply_header(self):
        '''
        The CoD4 server appends four bytes of 0xFF, the string
        'print' and a new-line to each new batch of data sent
        in response to a command.
        '''
        try:
            return self._reply_header
        except AttributeError:
            data = [self._PREFIX_BYTE] * 4
            data.extend(map(ord,'print\n'))
            self._reply_header = bytes(data)
        return self._reply_header

    def send(self,message,encoding='utf-8',timeout=0.05,retries=2):
        '''

        :param: message  - string holding command to send to server
        :param: encoding - string used to determine byte buffer [en|de]coding
        :param: timeout  - float seconds to wait for a response 
        :param: retries  - integer number of times to timeout before failing

        :return: string server response to client message

        Sends 'message' to the server and waits for a response,
        which is returned to the caller.

        Raises UsageError if the strings 'usage:' or 'unknown command'
        are present in the data returned from the remote console.

        If no data is received after (timeout * retries) seconds, the
        NoResponseError exception is raised which will contain the
        message that was not acknowledged and the timeout and retries
        used.

        Finally, this method will raise ServerPasswordNotSet if the server 
        complains that it's rcons_password is unset.

        '''

        text = super(RemoteConsole,self).send(message,encoding,timeout,retries)
                                              
        lctext = text[:32].lower()

        for phrase in [ 'usage:','unknown command' ]:
            if lctext.count(phrase):
                raise UsageError(message,text)

        if text.startswith("The server must set 'rcon_password'"):
            raise ServerPasswordNotSet(text)

        return text

    def clean(self,text):
        '''
        :param: text - string
        :return: string

        CoD4 embeds ^[0-9] codes in text to specify text color 
        and is over-enthusiastic with its use of double quotes.
        '''
        return super(RemoteConsole,self).clean(text,[('^',2), ('"',1)])

    def _list(self,cmd,filterfunc=None):
        '''
        :param: cmd        - string
        :param: filterfunc - function used to filter strings

        :return: list of strings

        This method sends the specified command to the server and
        then splits the response text by new-lines.  The filterfunc
        parameter allows callers to provide functions to apply
        custom filtering to the response.  By default, the empty lines
        are filtered out.  The server response is returned to the caller
        split into lines of strings.

        Note: filterfunc should return True for lines that should be
              kept and False for lines that should be ignored.
        '''
        
        if filterfunc is None:
            filterfunc = lambda x: len(x)
            
        return [x for x in self.send(cmd).split('\n') if filterfunc(x)]

    def _get_dvar_value(self,name):
        return self.dvardump(name)[name]    

    @property
    def bindlist(self):
        '''
        A dictionary of Keyboard_Key,Command pairs.
        '''
        l = {}
        for pair in self._list('bindlist'):
            if len(pair) == 0:
                continue
            key,val = pair.split(maxsplit=1)
            l.setdefault(key,val.replace('"',''))
        return l
    
    @property
    def channels(self):
        '''
        List of all "channels".
        '''
        return self._list('con_channellist')

    @property
    def visible_channels(self):
        '''
        List of all visible "channels".
        '''
        return self._list('con_visiblechannellist')
    
    @property
    def cmdlist(self):
        '''
        Sorted list of commands supported by the server.
        '''
        cmds = self._list('cmdlist')[:-1]
        cmds.sort()
        return cmds

    @property
    def dvarlist(self):
        '''
        List of dvars without their current defined values.
        '''
        dvars = []
        for line in self._list('dvarlist')[:-1]:
            name,_,value = line.partition('"')
            dvars.append(name.split()[-1])
        return dvars
    
    @property
    def fullpath(self):
        '''
        Results of the 'fullpath' command.
        '''
        return self.send('fullpath')

    @property
    def meminfo(self):
        '''
        Results of the 'meminfo' command.
        '''
        return self.send('meminfo')

    @property
    def net_dumpprofile(self):
        '''
        Results of the 'net_dumpprofile' command.
        '''
        return self.send('net_dumpprofile')

    @property
    def language(self):
        '''
        The current language in use for localization.
        '''
        text = self._list('path')
        return text[0].split()[-1]

    @property
    def fileHandles(self):
        '''
        List of currently open file handles.
        '''
        fh = []
        for line in self._list('path'):
            if line.startswith('handle'):
                fh.append(line.split()[-1])
        return fh
    
    @property
    def path(self):
        '''
        A list of paths used to search for in-game assets.
        '''
        p = []
        for line in self._list('path'):
            if line.startswith('/'):
                p.append(line.partition('(')[0])
        return p
    
    @property
    def players(self):
        '''
        List of players currently connected.
        '''
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
        '''
        Results of the 'scriptUsage' command.
        '''
        return self.send('scriptUsage')

    @property
    def status(self):
        '''
        Results of the 'status' command.
        '''
        return self.send('status')

    def _info(self,which,pause=0.5):
        '''

        :param: which - string, either 'serverinfo' or 'systeminfo'
        :param: pause - float seconds to pause between commands.
        :return: dictionary

        The systeminfo and serverinfo commands return key/value pairs,
        however the column width alloted for the key name isn't
        quite wide enough and key names can run into their values.
        This renders the pair unsplittable.
        
        In this case, the key name is disambiguated by searching the
        dvar name space for a matching key and associated value from
        a previous dvardump.
        
        A half-second pause between the dvardump and issuing the
        [system|server]info command prevents back-to-back commands
        and interlaced server responses.
        '''

        if not which in ['serverinfo','systeminfo']:
            raise ValueError('%s not serverinfo or systeminfo' % (which))
        
        dvars = self.dvardump()
        
        sleep(pause)
        
        d = {}
        for entry in self._list(which)[1:]:
            fields = entry.split(maxsplit=1)
            if len(fields) == 2:
                d.setdefault(fields[0],fields[1])
                continue

            for key,value in dvars.items():
                if fields[0].startswith(key):
                    d.setdefault(key,value)
                    break
        return d
        
    @property
    def serverinfo(self):
        '''
        Dictionary results of the 'serverinfo' command.
        '''
        return self._info('serverinfo')

    @property
    def systeminfo(self):
        '''
        Dictionary results of the 'systeminfo' command.
        '''
        return self._info('systeminfo')

    ## read/write properties

    @property
    def mapname(self):
        '''
        The map currently in use.
        '''
        return self._get_dvar_value('mapname')

    @mapname.setter
    def mapname(self,mapname):
        '''
        :param: mapname - string
        Set the current map to a new value.
        '''
        self.map(mapname)

    @property
    def gametype_default(self):
        '''
        '''
        return self._gametype_for('default:')

    @property
    def gametype_next(self):
        '''
        '''
        return self._gametype_for('latched:')

    @property
    def gametype(self):
        '''
        '''
        return self._gametype_for('is:')    

    @gametype.setter
    def gametype(self,newGametype):
        '''
        '''
        result = self.send('g_gametype %s' % (newGametype))

    @property
    def gamename(self):
        return self._get_dvar_value('sv_hostname')

    @gamename.setter
    def gamename(self,newName):
        self.send('sv_hostname %s' % (newName))

    @property
    def password(self):
        return self._get_dvar_value('g_password')

    @password.setter
    def password(self,newPassword):
        self.send('g_password %s' % (newPassword))

    @property
    def rcon_password(self):
        return self._get_dvar_value('rcon_password')

    @rcon_password.setter
    def rcon_password(self,newPassword):
        self.send('rcon_password %s' % (newPassword))

    @property
    def friendly_fire(self):
        return self._get_dvar_value('ui_friendlyfire')

    @friendly_fire.setter
    def friendly_fire(self,newValue):

        ffex = ValueError("friendly_fire = 0|off,1|on,2|reflect")

        if issubclass(type(newValue),str):
            try:
                newValue = {'off':0,'on':1,'reflect':2}[newValue]
            except KeyError:
                raise ffex
        else:
            if int(newValue) not in [0,1,2]:
                raise ffex
        
        self.send('ui_friendlyfire %s' % (newValue))
 
    # player kick / ban

    def ban(self,player,temporary=True):
        '''
        :param: player - string or integer

        Bans a player from the server.
        '''

        if issubclass(type(player),str):
            cmd = {True:'tempBanUser',False:'banUser'}[temporary]
        else:
            cmd = {True:'tempBanClient',False:'banClient'}[temporary]
                   
        results = self.send('%s %s' % (cmd,player))

    def unban(self,playerName):
        '''
        :param: playerName - string

        Removes a player from banned list.
        '''
        result = r.send('unbanUser %s' % (playerName))

        
    def kick(self,player):
        '''
        :param: player - string or integer

        Kicks a player off the server, however they are not banned.

        If 'playerName' is 'all', all players are kicked from the server.
        '''
        
        cmd = {True:'kickonly', False:'kickclient'}[issubstring(player,str)]
        
        results = self.send('%s %s' % (cmd,player))



    ## methods with arguments    

    def bind(self,key,command=''):
        '''
        :param: key     - string
        :param: command - string

        Bind a command to a keyboard key.

        Returns the current binding if 'command' is not specified.
        '''
        
        message = 'bind %s %s' % (key,command)
        result = self.send(message)
        
        if result.count('valid key'):
            raise UsageError(message,result)
        
        if result.count('='):
            key,cmd = self.clean(result).split('=')
            return {key.strip():cmd.strip()}

    def channel(self,channel,hide=False):
        '''
        :param: channel - string, see 'channels' property
        :param: hide    - bool hides the specified channel if True
        :return: string results of the command if any

        This method is used to control what screen elements are visible.

        EJO - I think.

        '''
        
        cmd = { True:'con_hidechannel',False:'con_showchannel'}[hide]
        
        results = self.send('%s %s' % (cmd,channel))

    def chatmode(self,mode='team'):
        '''
        :param: mode - string, either 'team' or 'public'.
        '''
        self.send('chatmode%s'%(mode))
        
    def dir(self,path='.',ext=''):
        '''
        :param: path - string path to return results for
        :param: ext  - string filter by extension
        :return: list of strings

        List files in a directory.

        The path may contain '*' or '?' wildcard characters. If
        it does, the 'ext' parameter will be ignored.

        '''
        if ('*' in path) or ('?' in path):
            files = self._list('fdir %s' %(path))
            del(files[0])
            del(files[-1])
        else:
            files = self._list('dir %s %s' % (path,ext))
            del(files[0:2])
        return files

    def dumpuser(self,playerName):
        '''
        :param: playerName - string 
        :return: dictionary of values associated with this player
        '''
        
        results = self._list('dumpuser %s' %(playerName))
        
        if results[0].lower().count('not on the server'):
            raise PlayerNotFound(user) # XXX exception or empty dict?
        d = {}
        for pair in results[2:]:
            key,value = pair.split()
            d.setdefault(key,value)
        return d

    def dvardump(self,name=''):
        '''
        :param: name - string dvar name
        :return: dictionary of key/value pairs

        If name is not specified, returns a dictionary of all 
        currently defined dvars.

        If name is specified, returns a dictonary of all dvars
        matching the given name.
        '''
        
        good = lambda t: len(t) and '==' not in t
        dlist = self._list('dvardump %s' % name,good)
        total = int(dlist[-2].split()[0])
        dvars = {}
        for data in dlist[:-2]:
            key,rawvalue = data.split(maxsplit=1)
            dvars.setdefault(key,self.clean(rawvalue))
        return dvars

        

    def dvar_int(self,name,value,minimum,maximum):
        '''
        :param: name    - string
        :param: value   - integer
        :param: minimum - integer
        :param: maximum - integer

        :return: the result of 'dvar_int' with parameter values

        '''
        msg = 'dvar_int %s %s %s %s'
        msg %= (name,value,minimum,maximum)
        result = self.send(msg)

    def dvar_float(self,name,value,minimum,maximum):
        '''
        :param: name    - string
        :param: value   - float
        :param: minimum - float
        :param: maximum - float

        :return: the result of 'dvar_float' with parameter values

        '''
        msg = 'dvar_float %s %s %s %s'
        msg %= (name,value,minimum,maximum)
        result = self.send(msg)

    def dvar_bool(self,name,value):
        '''
        :param: name    - string
        :param: value   - bool

        :return: the result of 'dvar_bool' with parameter values

        '''
        result = self.send('dvar_bool %s' % (value))
            
    def execute(self,filename):
        '''
        :param: filename - string

        :return: results of the 'exec <filename>' command.

        '''
        results = self.send('exec %s' % (filename))

    def gamecomplete(self):
        '''
        Tell the server to send a 'gamecomplete' message to metaserver.

        EJO - I guess.
        '''
        
        results = self.send('gamecompletestatus')


    def _gametype_for(self,which):
        '''
        :param: which - string 
        :return: string name of requested gametype

        The which parameter should be one of 'is:', 'default:' or
        'latched:'.  See gametype, gametype_default and gametype_next
        properties.
        '''

        if which not in ['is:','default:','latched:']:
            msg = "got %s expected 'is:','default:' or 'latched:'"%(which)
            raise ValueError(msg)
        
        results = self.send('g_gametype')
        
        return self.clean(results.partition(which)[2].split()[0])

    
    def heartbeat(self):
        '''
        Returns the results of the 'heatbeat' command.
        '''
        results = self.send('heartbeat')
        
    def map(self,mapname,cheats=False):
        '''
        :param: mapname - string 
        :param: cheats  - boolean
        
        Directs the server to stop the current map and start the
        supplied mapname.  If cheats is True, the 'devmap' command
        is used instead of 'map' allowing the manipulation of dvars
        that normally are read-only.

        If the specified file is not found FileNotFound is raised.

        '''
        
        cmd = {True:'devmap',False:'map'}[cheats]
        
        results = self.send('%s %s' % (cmd,mapname),timeout=0.25,retries=3)
        
        if results[-3].count('Error'):
            raise FileNotFound(mapname)

    def net_restart(self):
        '''
        Returns the results of the 'net_restart' command.
        '''
        result = self.send('net_restart')


    def quit(self,really=False):
        '''
        :param: really - bool

        Causes the remote server to quit, not client. 

        Invoke with a True if you mean it.
        '''
        
        if really:
            self.send('quit')

    # missing all the ragdoll commands

    def say(self,message):
        '''
        '''
        result = self.send('say %s' % message)

    def tell(self,playerName,message):
        '''
        '''
        result = self.send('tell %s %s' % (playerName,message))

    def next_map(self):
        '''
        '''
        result = self.send('map_rotate')

    def kick(self,player):
        '''
        '''
        result = self.send('kick %s' % player)

    def killserver(self):
        '''
        The server stops but the server process doesn't exit.

        Weird but ok.
        '''
        result = self.send('killserver')

    def restart(self,fast=False):
        '''
        :param: fast - bool
        
        If fast is True, calls fast_restart without re-reading assets.
        
        Otherwise, map_restart is used which re-read assets.
        '''
        if fast:
            result = self.send('fast_restart')
        else:
            result = self.send('map_restart',timeout=0.25)

    def reset(self,dvarname):
        '''
        :param: dvarname - string
        '''
        results = self.send('reset %s' %(dvarname))

    def resetStats(self):
        '''
        '''
        results = self.send('resetStats')

    def selectStringTableEntryInDvar(self,index):
        '''
        '''
        pass

    def set(self,name,value):
        '''
        set value of an existing variable
        '''
        results = self.send('set %s %s' % (name,value))

    def seta(self,name,value):
        '''
        create a new variable and set it's value
        '''
        results = self.send('seta %s %s' % (name,value))

    def setu(self,name,value):
        '''
        set a variable for a user
        '''
        results = self.send('setu %s %s' % (name,value))

    def sets(self,name,value):
        '''
        set a variable for the server
        '''
        results = self.send('set %s %s' % (name,value))        

    def setPerk(self,user,perk):
        '''
        '''
        results = self.send('setPerk %s %s' %(user,perk))

    def setDvarToTime(self,dvarname):
        '''
        '''
        results = self.send('setdvartotime %s' %(dvarname))

    def setfromdvar(self,name,dvarname):
        '''
        '''
        results = self.send('setfromdvar %s %s' %(name,dvarname))

    def setfromlocstring(self,name,string):
        '''
        localized string getter 
        '''
        result = self.send('setfromlocstring %s %s' %(name,string))

    def statGetInDvar(self,index,dvarname):
        '''
        '''
        return self.send('statgetindvar %s %s' % (index,dvarname))

    def statSet(self,index,value):
        '''
        '''
        results = self.send('statSet %s %s' % (index,value))

    def tempBanClient(self,clientNumber):
        '''
        '''
        results = self.send('tempBanClient %s' % (clientNumber))

    def tempBanUser(self,user):
        '''
        '''
        results = self.send('tempBanUser %s' % (user))

    def timedemo(self):
        '''
        '''
        pass

    def toggle(self,name):
        '''
        '''
        results = self.send('toggle %s' % (name))
        
    def togglep(self,name,optionals=''):
        '''
        '''
        results = self.send('togglep %s %s' %(name,optionals))
        
    def toggleMenu(self):
        '''
        '''
        results = self.send('toggleMenu')

    def touchFile(self):
        '''
        '''
        pass

    def unbanUser(self,user):
        '''
        '''
        results = self.send('unbanUser %s' % (user))

    def unbind(self,key=None):
        '''
        '''
        if key is None:
            results = self.send('unbindall')
        else:
            results = self.send('unbind %s' %(key))

    def unskippableCinematic(self):
        '''
        '''
        pass

    def uploadStats(self):
        '''
        '''
        pass

    def vstr(self,string):
        '''
        '''
        results =self.send('vstr %s' % (string))

    def wait(self):
        '''
        '''
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

#r = RemoteConsole('foobar')

