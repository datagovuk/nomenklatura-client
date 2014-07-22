from ConfigParser import SafeConfigParser
import json
import os

import requests


class _NomenklaturaObject(object):
    """ The basic object we'll be inheriting from """

    WRITE_ATTRS = []

    def __init__(self, data):
        self.__data__ = data

    def __getattr__(self, k):
        return self.__data__[k]

    def __setattr__(self, k, v):
        if k in self.WRITE_ATTRS:
            self.__data__[k] = v
        else:
            super(_NomenklaturaObject, self).__setattr__(k, v)



class NomenklaturaException(Exception):
    
    def __init__(self, message):
        self.message = message 

    def __unicode__(self):
        return unicode(self.message)

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __repr__(self):
        return '<NomenklaturaException("%s")>' % self.message


class NomenklaturaServerException(NomenklaturaException):

    def __init__(self, response):
        self.status = response.get('status')
        self.name = response.get('name')
        self.message = response.get('message', response.get('description'))
        self.description = response.get('description')
        self.data = response


class InvalidRequest(NomenklaturaServerException): pass
class NoMatch(NomenklaturaServerException): pass


class _Client(object):
    """ Nomenklatura client class; handles configuration and network
    settings. Do not instantiate directly, use ``Dataset`` instead. """

    def __init__(self, api_host, api_key, api_prefix='/api/2/'):
        config = SafeConfigParser()
        config.read([os.path.expanduser('~/.nomenklatura.ini')])
        if config.has_section('client'):
            config = dict(config.items('client'))
        else:
            config = {}

        if not api_host:
            api_host = os.environ.get('NOMENKLATURA_HOST',
                config.get('host', 'http://nomenklatura.okfnlabs.org'))

        if not api_key:
            api_key = os.environ.get('NOMENKLATURA_APIKEY',
                config.get('api_key'))

        if api_host.endswith('/') and api_prefix.startswith('/'):
            api_prefix = api_prefix[1:]
        self.api_host = api_host
        self.api_key = api_key
        self.api_prefix = api_prefix

    @property
    def session(self):
        if not hasattr(self, '_session'):
            headers = {'Accept': 'application/json',
                       'Content-Type': 'application/json'}
            if self.api_key:
                    headers['Authorization'] = self.api_key
            self._session = requests.Session()
            self._session.headers.update(headers)
        return self._session

    def path(self, endpoint):
        if endpoint.startswith(self.api_host + self.api_prefix):
            return endpoint
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        return self.api_host + self.api_prefix + endpoint

    def evaluate(self, response):
        try:
            data = response.json()
        except ValueError:
            raise NomenklaturaException('Server did not respond with JSON data.')
        if (not response.ok) and 'status' in data and 'message' in data:
            raise NomenklaturaServerException(data)
        return response.status_code, data

    def get(self, endpoint, params={}):
        response = self.session.get(self.path(endpoint), params=params)
        return self.evaluate(response)

    def post(self, endpoint, data={}):
        data = json.dumps(data)
        response = self.session.post(self.path(endpoint),
            allow_redirects=True, data=data)
        return self.evaluate(response)


class Entity(_NomenklaturaObject):
    """ Entities are the central domain object of nomenklatura. """

    WRITE_ATTRS = ['name', 'invalid', 'reviewed', 'canonical', 'attributes']

    def __init__(self, client, data):
        self._client = client
        super(Entity, self).__init__(data)

    def __repr__(self):
        return "<Entity(%s:%s:%s:%s)>" % (self.dataset, self.id, str(self), self.canonical)

    def __str__(self):
        return self.name.encode('ascii', 'replace')

    def __unicode__(self):
        return self.name

    def update(self):
        self._client.post('/entities/%s' % self.id, data=self.__data__)

    def dereference(self):
        if self.canonical is not None:
            return self.canonical.dereference()
        return self

    @property
    def is_alias(self):
        return self.canonical is not None

    @property
    def canonical(self):
        cv = self.__data__.get('canonical')
        if cv is not None:
            return Entity(self._client, cv)

    @property
    def aliases(self):
        """ Returns a generator of all aliases of this entity. """
        _, res = self._client.get('/entities/%s/aliases' % self.id)
        while True:
            for entity in res.get('results'):
                yield Entity(self._client, entity)
            if res.get('next') is None:
                break
            _, res = self._client.get(res.get('next'))



class Dataset(_NomenklaturaObject):
    """ A Nomenklatura dataset. Each dataset contains a set of entities. """

    def __init__(self, dataset, api_host=None, api_key=None):
        self.name = dataset
        self._client = _Client(api_host=api_host, api_key=api_key)
        _, data = self._client.get('/datasets/' + self.name)
        super(Dataset, self).__init__(data)    

    def entities(self, filter_name=None):
        """ Returns a generator of all entities in the dataset """
        params = {'dataset': self.name, 'filter_name': filter_name}
        _, res = self._client.get('/entities', params=params)
        while True:
            for entity in res.get('results'):
                yield Entity(self._client, entity)
            if res.get('next') is None:
                break
            _, res = self._client.get(res.get('next'))

    def entity_by_name(self, name):
        try:
            _, res = self._client.get('/datasets/%s/find' % self.name,
                params={'name': name})
            return Entity(self._client, res)
        except NomenklaturaServerException, nse:
            if nse.status == 404:
                raise NoMatch(nse.data)
            raise

    def entity_by_id(self, id):
        _, res = self._client.get('/entities/%s' % id)
        return Entity(self._client, res)

    def create_entity(self, name, attributes={}, reviewed=False,
        invalid=False, canonical=None, **kw):
        kw.update({
            'name': name,
            'attributes': attributes,
            'reviewed': reviewed,
            'invalid': invalid,
            'canonical': canonical,
            'dataset': self.name
            })
        status_code, res = self._client.post('/entities', data=kw)
        if status_code == 400:
            raise InvalidRequest(res)
        return Entity(self._client, res)

    def __repr__(self):
            return "<Dataset(%s)>" % self.name
