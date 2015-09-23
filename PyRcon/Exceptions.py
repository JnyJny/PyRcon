
class NoResponseError(Exception):
    pass

class UsageError(Exception):
    pass

class PlayerNotFound(Exception):
    pass


#    def __init__(self,command,message):
#        self.command = command
#        self.message = message
#
#    def __str__(self):
#        return '%s resulted in %s' % (self.command,self.message)
