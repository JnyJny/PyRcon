
try:
    __import__('pkg_resources').declare_namespace(__name__)
except:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)

#from .CoD4 import RemoteConsole as CoD4RemoteConsole

__all__ = ['QuakeStyleRemoteConsole','CoD4']

