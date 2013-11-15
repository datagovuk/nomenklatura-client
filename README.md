Python client for nomenklatura
==============================

This is a very simple wrapper for the [nomenklatura API](http://nomenklatura.okfnlabs.org) to allow Python application to
transparently handle reconciliation requests via the nomenklatura web
service. See the API docs for a usage example. 

usage::

   import nomenklatura
   dataset=nomenklatura.Dataset("offenesparlament")
   entity=dataset.lookup("Angela Merkel")
   print entity

