import rez_pip.plugins


def initializePluginManager(name: str):
    """Initialize a plugin manager and clear the cache before exiting the function

    :param name: Name of the plugin to load.
    """
    manager = rez_pip.plugins.getManager()
    for name, plugin in manager.list_name_plugin():
        if not name.startswith(f"rez-pip.plugins.{name}"):
            manager.unregister(plugin)

    try:
        yield manager
    finally:
        del manager
        rez_pip.plugins.getManager.cache_clear()
