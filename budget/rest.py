class RESTResource(object):
    """Represents a REST resource, with the different HTTP verbs"""
    _NEED_ID = ["get", "update", "delete"]
    _VERBS = {"get": "GET",
              "update": "PUT",
              "delete": "DELETE",
              "list": "GET",
              "add": "POST",}

    def __init__(self, name, route, app, actions, handler, authentifier):
        """
        :name:
            name of the resource. This is being used when registering
            the route, for its name and for the name of the id parameter
            that will be passed to the views

        :route:
           Default route for this resource

        :app:
            Application to register the routes onto

        :actions: 
            Authorized actions.

        :handler:
            The handler instance which will handle the requests

        :authentifier:
            callable checking the authentication. If specified, all the 
            methods will be checked against it.
        """

        self._route = route
        self._handler = handler
        self._name = name
        self._identifier = "%s_id" % name
        self._authentifier = authentifier

        for action in actions:
            self.add_url_rule(app, action)
    
    def _get_route_for(self, action):
        """Return the complete URL for this action.

        Basically:
        
         - get, update and delete need an id
         - add and list does not
        """
        route = self._route

        if action in self._NEED_ID:
            route += "/<%s>" % self._identifier
        
        return route

    def add_url_rule(self, app, action):
        """Registers a new url to the given application, regarding 
        the action.
        """
        method = getattr(self._handler, action)

        # decorate the view
        if self._authentifier:
            method = need_auth(self._authentifier, self._name)(method)

        app.add_url_rule(
            self._get_route_for(action),
            "%s_%s" % (self._name, action),
            method,
            methods=[self._VERBS.get(action, "GET")])


def need_auth(authentifier, name=None):
    """Decorator checking that the authentifier does not returns false in 
    the current context.

    If the request is authorized, the object returned by the authentifier
    is added to the kwargs of the method.

    If not, issue a 403 Forbidden error

    :authentifier:
        The callable to check the context onto.

    :name:
        **Optional**, name of the argument to put the object into.
        If it is not provided, nothing will be added to the kwargs
        of the decorated function
    """
    def wrapper(func):
        def wrapped(*args, **kwargs):
            result = authentifier(*args, **kwargs)
            if result:
                if name:
                    kwargs[name] = result
                return func(*args, **kwargs)
            else:
                raise werkzeug.exceptions.Forbidden()
        return wrapped
    return wrapper


class DefaultHandler(object):

    def add(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def list(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        pass
