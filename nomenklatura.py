import requests
import json


class NKObject(object):
  """ The basic Object we'll be inheriting from """

  def __init__(self, data):
      self.__data__ = data

  def __getattr__(self, k):
      return self.__data__[k]

  def __str__(self):
      return self.__repr__()


class NKException(Exception, NKObject):
    def __init__(self, data):
        NKObject.__init__(self, data)


class DatasetException(NKException):

    def __repr__(self):
        return "<DatasetException(%s:%s)>" % (self,
            getattr(self, 'message', None))


class NoMatch(NKException):

    def __repr__(self):
        return "<NoMatch(%s:%s)>" % (self.dataset, self.name)


class Invalid(NKException):

    def __repr__(self):
        return "<Invalid(%s:%s)>" % (self.dataset, self.name)


NKObject.DatasetException = DatasetException
NKObject.NoMatch = NoMatch
NKObject.Invalid = Invalid


class Entity(NKObject):

  def __init__(self, dataset, data):
    self._dataset = dataset
    super(Entity, self).__init__(data)

  def __repr__(self):
    return "<Value(%s:%s:%s)>" % (self._dataset.name,
                                  self.id, self.name)

  def __str__(self):
    return self.name


class Alias(NKObject):

  INVALID = "INVALID"
  NEW = "NEW"

  def __init__(self, dataset, data):
      self._dataset = dataset
      super(Alias, self).__init__(data)

  def __repr__(self):
      return "<Link(%s:%s:%s:%s)>" % (self._dataset.name,
            self.id, self.name, self.is_matched)


class Dataset(NKObject):
  """ A Nomenklatura dataset. Helps you to access entities and aliases from
  Nomenklatura...

  Dataset(name,host="http://nomenklatura.okfnlabs.org",api_key=None)

  usage:

    from nomenklatura import dataset
    ds=Dataset("offenesparlament")
    ds.lookup("Angela Merkel")

  Methods defined here:

    get_entity(id=None,name=None) """

  def __init__(self, dataset,
               host='http://nomenklatura.okfnlabs.org',
               api_key=None):
      self.host = host
      self.name = dataset
      self.api_key = api_key
      self._fetch()

  @property
  def _session(self):
      if not hasattr(self, '_session_obj'):
          headers = {'Accept': 'application/json',
                     'Content-Type': 'application/json'}
          if self.api_key:
              headers['Authorization'] = self.api_key
          self._session_obj = requests.Session()
          self._session_obj.headers.update(headers)
      return self._session_obj

  def _get(self, path, params={}, retry=True):
      response = self._session.get(self.host + '/' + self.name + path,
                                   params=params)
      if not response.ok:
          #print [response.status_code, response.content]
          del self._session_obj
      return response.status_code, response.json()

  def _post(self, path, data={}, retry=True):
      data = json.dumps(data)
      response = self._session.post(self.host + '/' + self.name + path,
                                    allow_redirects=True,
                                    data=data)
      if not response.ok:
          #print [response.status_code, response.content]
          del self._session_obj
      return (response.status_code,
              json.loads(response.content) if response.content else {})

  def _fetch(self):
      code, data = self._get('')
      if not (code == 200 and data):
          data = data or {'code': code}
          raise self.DatasetException(data)
      super(Dataset,self).__init__(data)    

  def get_entity(self, id=None, name=None):
    """ get an entity from the dataset 
        get_entity(id=23) -> get entity with id 23
        get_entity(name="FOO") -> get entity with value "FOO"

        if neither id nor value are specified - raises a Value
        Error
    """

    if not (id or name):
      raise ValueError("Need to give an ID or a name")
    if id is not None:
        code, val = self._get('/entities/%s' % id)
    else:
        code, val = self._get('/entities', params={'name': name})
    if code != 200:
        raise self.NKException(val or {})
    return Entity(self, val)

  def add_entity(self, name, data={}):
    """ Add an entity to the dataset """
    code, val = self._post('/entities',
        data={'name': name, 'data': data})
    if code == 400:
        raise self.NKException(val)
    return Value(self, val)

  def ensure_entity(self, name, data={}):
    """ Makes sure you have an entity to work with:
    ensure_entity(name, data) ->
        Returns an Entity if it exists - adds the entity otherwise"""
    try:
        return self.get_value(value=value)
    except self.NKException:
        return self.add_value(value=value, data=data)

  def entities(self):
      """ Returns a generator of all entities in the dataset """
      code, vals = self._get('/entities')
      return (Entity(self, v) for v in vals) 

  def get_alias(self, id=None, name=None):
      if not (id or name):
        raise ValueError("Need to give an ID or a name")
      if id:
          code, val = self._get('/aliases/%s' % id)
      else:
          code, val = self._get('/aliases', params={'name': name})
      if code != 200:
          raise self.NKException(val)
      return Alias(self, val)

  def aliases(self):
      """ Returns a generator of all aliases in the dataset """
      code, vals = self._get('/aliases')
      return (Alias(self, v) for v in vals)

  def lookup(self, name, context={}, readonly=False):
      code, val = self._post('/lookup',
            data={'name': name, 'readonly': readonly})
      if code == 404:
          raise self.NoMatch(val)
      elif code == 418:
          raise self.Invalid(val)
      else:
          return Entity(self, val.get('entity'))

  def match(self, alias_id, entity_id):
      code, val = self._post('/aliases/%s/match' % alias_id,
              data={'choice': entity_id, 'name': ''})
      if code != 200:
          raise self.NKException(val)
      return None

  def __repr__(self):
      return "<Dataset(%s)>" % self.name

if __name__ == "__main__":
    ds = Dataset('offenesparlament')
