Quickstart
==========
Instantiate a new client
------------------------
Use this code to instantiate a client and get your login status. CDF returns an object with
attributes that describe which project and service account your API key belongs to. The :code:`client_name`
is a user-defined string intended to give the client a unique identifier. You
can provide the :code:`client_name` by passing it directly to the :code:`ClientConfig` constructor.

The Cognite API uses OpenID Connect (OIDC) to authenticate.
Use one of the credential providers such as OAuthClientCredentials to authenticate:

.. note::
    The following example sets a global client configuration which will be used if no config is
    explicitly passed to `CogniteClient`_.
    All examples in this documentation assume that such a global configuration has been set.

.. code:: python

    from cognite.client import CogniteClient, ClientConfig, global_config
    from cognite.client.credentials import OAuthClientCredentials

    # This value will depend on the cluster your CDF project runs on
    cluster = "api"
    base_url = f"https://{cluster}.cognitedata.com"
    tenant_id = "my-tenant-id"
    client_id = "my-client-id"
    # client secret should not be stored in-code, so we load it from an environment variable
    client_secret = os.environ["MY_CLIENT_SECRET"]
    creds = OAuthClientCredentials(
      token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
      client_id=client_id,
      client_secret=client_secret,
      scopes=[f"{base_url}/.default"]
    )

    cnf = ClientConfig(
      client_name="my-special-client",
      base_url=base_url,
      project="my-project",
      credentials=creds
    )

    global_config.default_client_config = cnf
    c = CogniteClient()

Examples for all OAuth credential providers can be found in the `Credential Providers`_ section.

You can also make your own credential provider:

.. code:: python

    from cognite.client import CogniteClient, ClientConfig
    from cognite.client.credentials import Token

    def token_provider():
        ...

    cnf = ClientConfig(
      client_name="my-special-client",
      base_url="https://<cluster>.cognitedata.com",
      project="my-project",
      credentials=Token(token_provider)
    )
    c = CogniteClient(cnf)

Discover time series
--------------------
For the next examples, you will need to supply ids for the time series that you want to retrieve. You can find some ids by listing the available time series.
Limits for listing resources default to 25, so the following code will return the first 25 time series resources.

.. code:: python

    from cognite.client import CogniteClient

    c = CogniteClient()
    ts_list = c.time_series.list()

Create an asset hierarchy
-------------------------
CDF organizes digital information about the physical world. Assets are digital representations of physical objects or
groups of objects, and assets are organized into an asset hierarchy. For example, an asset can represent a water pump
which is part of a subsystem on an oil platform.

At the top of an asset hierarchy is a root asset (e.g., the oil platform). Each project can have multiple root assets.
Note that all assets must have a name (a non-empty string).

To create a root asset (an asset without a parent), omit the parent ID when you post the asset to the API.
To make an asset a child of an existing asset, you must specify a parent ID (or parent external ID):

.. code:: python

    from cognite.client import CogniteClient
    from cognite.client.data_classes import Asset

    c = CogniteClient()
    my_asset = Asset(name="my first child asset", parent_id=123)
    c.assets.create(my_asset)

To post an entire asset hierarchy, you can describe the relations within your asset hierarchy
using the ``external_id`` and ``parent_external_id`` attributes on the ``Asset`` object. You can post
an arbitrary number of assets, and the SDK will split the request into multiple requests. To make sure that the
assets are created in the correct order, you can use the ``create_hierarchy()`` function, which takes care of the
topological sorting for you, before splitting the request into smaller chunks. However, note that the ``create_hierarchy()``
function requires the ``external_id`` property to be set for all assets.

This example shows how to post a three levels deep asset hierarchy consisting of three assets.

.. code:: python

    from cognite.client import CogniteClient
    from cognite.client.data_classes import Asset

    c = CogniteClient()
    root = Asset(name="root", external_id="1")
    child = Asset(name="child", external_id="2", parent_external_id="1")
    descendant = Asset(name="descendant", external_id="3", parent_external_id="2")
    c.assets.create_hierarchy([root, child, descendant])

Wrap the ``create_hierarchy()`` call in a try-except to get information if creating the assets fails:

- Which assets were created. (The request yielded a 201.)
- Which assets may have been created. (The request yielded 5xx.)
- Which assets were not created. (The request yielded 4xx, or was a descendant of another asset which may or may not have been created.)

.. code:: python

    from cognite.client.exceptions import CogniteAPIError
    try:
        c.assets.create_hierarchy([root, child, descendant])
    except CogniteAPIError as err:
        created = err.successful
        maybe_created = err.unknown
        not_created = err.failed

Prior to creating the Assets, it might be useful to do some validation on the assets you have. To do this without
potentially sending API requests, import and use :class:`~cognite.client.data_classes.assets.AssetHierarchy`:

.. code:: python

    from cognite.client.data_classes import AssetHierarchy
    hierarchy = AssetHierarchy(assets)
    # Get a report written to the terminal listing any issues:
    hierarchy.validate_and_report()
    # If there are issues, you may inspect them directly:
    if not hierarchy.is_valid():
        hierarchy.orphans
        hierarchy.invalid
        hierarchy.unsure_parents
        hierarchy.duplicates
        hierarchy.cycles  # Requires no other basic issues

Note that validation will run automatically for you when calling ``create_hierarchy()``. You may choose to catch
``CogniteAssetHierarchyError`` and inspect any raised issues:

.. code:: python

    from cognite.client.exceptions import CogniteAssetHierarchyError
    try:
        c.assets.create_hierarchy(assets)
    except CogniteAssetHierarchyError as err:
        # You may inspect the following attributes:
        err.orphans
        err.invalid
        err.unsure_parents
        err.duplicates
        err.cycles  # Requires no other basic issues

Retrieve all events related to an asset subtree
-----------------------------------------------
Assets are used to connect related data together, even if the data comes from different sources; Time series of data
points, events and files are all connected to one or more assets. A pump asset can be connected to a time series
measuring pressure within the pump, as well as events recording maintenance operations, and a file with a 3D diagram
of the pump.

To retrieve all events related to a given subtree of assets, we first fetch the subtree under a given asset using the
:code:`.subtree()` method. This returns an :code:`AssetList` object, which has a :code:`.events()` method. This method will
return events related to any asset in the :code:`AssetList`.

.. code:: python

    from cognite.client import CogniteClient
    from cognite.client.data_classes import Asset

    c = CogniteClient()
    subtree_root_asset = "some-external-id"
    subtree = c.assets.retrieve(external_id=subtree_root_asset).subtree()
    related_events = subtree.events()

You can use the same pattern to retrieve all time series or files related to a set of assets.

.. code:: python

    related_files = subtree.files()
    related_time_series = subtree.time_series()

Settings
========
Client configuration
--------------------
You can pass configuration arguments directly to the `CogniteClient`_ constructor, for example to configure the base url of your requests and additional headers. For a list of all configuration arguments, see the `CogniteClient`_ class definition.

global configuration
-------------------------
You can set global configuration options like this:

.. code:: python

    from cognite.client import global_config, ClientConfig
    from cognite.client.credentials import Token
    global_config.default_client_config = ClientConfig(
        client_name="my-client", project="myproj", credentials=Token("verysecret")
    )
    global_config.disable_pypi_version_check = True
    global_config.disable_gzip = False
    global_config.disable_ssl = False
    global_config.max_retries = 10
    global_config.max_retry_backoff = 10
    global_config.max_connection_pool_size = 10
    global_config.status_forcelist = {429, 502, 503}

These must be set prior to instantiating a CogniteClient in order for them to take effect.

Concurrency and connection pooling
----------------------------------
This library does not expose API limits to the user. If your request exceeds API limits, the SDK splits your
request into chunks and performs the sub-requests in parallel. To control how many concurrent requests you send
to the API, you can either pass the :code:`max_workers` attribute when you instantiate the `CogniteClient`_ or set the :code:`max_workers` config option.

If you are working with multiple instances of `CogniteClient`_, all instances will share the same connection pool.
If you have several instances, you can increase the max connection pool size to reuse connections if you are performing a large amount of concurrent requests.
You can increase the max connection pool size by setting the :code:`max_connection_pool_size` config option.

Extensions and optional dependencies
====================================
Pandas integration
------------------
The SDK is tightly integrated with the `pandas <https://pandas.pydata.org/pandas-docs/stable/>`_ library.
You can use the :code:`.to_pandas()` method on pretty much any object and get a pandas data frame describing the data.

This is particularly useful when you are working with time series data and with tabular data from the Raw API.

How to install extra dependencies
---------------------------------
If your application requires the functionality from e.g. the :code:`pandas`, :code:`sympy`, or :code:`geopandas` dependencies,
you should install the SDK along with its optional dependencies. The available extras are:

- numpy: numpy
- pandas: pandas
- geo: geopanda, shapely
- sympy: sympy
- functions: pip
- all (will install dependencies for all the above)

These can be installed with the following command:

pip

.. code:: bash

    $ pip install "cognite-sdk[pandas, geo]"

poetry

.. code:: bash

    $ poetry add cognite-sdk -E pandas -E geo

API
===
CogniteClient
-------------
.. autoclass:: cognite.client.CogniteClient
    :members:
    :member-order: bysource

.. autoclass:: cognite.client.config.ClientConfig
    :members:
    :member-order: bysource

.. autoclass:: cognite.client.config.GlobalConfig
    :members:
    :member-order: bysource


Authentication
--------------
Credential Providers
^^^^^^^^^^^^^^^^^^^^
.. autoclass:: cognite.client.credentials.Token
    :members:
    :member-order: bysource
.. autoclass:: cognite.client.credentials.OAuthClientCredentials
    :members:
    :member-order: bysource
.. autoclass:: cognite.client.credentials.OAuthInteractive
    :members:
    :member-order: bysource
.. autoclass:: cognite.client.credentials.OAuthDeviceCode
    :members:
    :member-order: bysource
.. autoclass:: cognite.client.credentials.OAuthClientCertificate
    :members:
    :member-order: bysource

Assets
------
Retrieve an asset by id
^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.retrieve

Retrieve multiple assets by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.retrieve_multiple

Retrieve an asset subtree
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.retrieve_subtree

List assets
^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.list

Aggregate assets
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.aggregate

Aggregate asset metadata keys
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.aggregate_metadata_keys

Aggregate asset metadata values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.aggregate_metadata_values

Search for assets
^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.search

Create assets
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.create

Create asset hierarchy
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.create_hierarchy

Delete assets
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.delete

Update assets
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.assets.AssetsAPI.update

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.assets
    :members:
    :show-inheritance:

Labels
------

List labels
^^^^^^^^^^^
.. automethod:: cognite.client._api.labels.LabelsAPI.list

Create a label
^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.labels.LabelsAPI.create

Delete labels
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.labels.LabelsAPI.delete

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.labels
    :members:
    :show-inheritance:

Events
------
Retrieve an event by id
^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.retrieve

Retrieve multiple events by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.retrieve_multiple

List events
^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.list

Aggregate events
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.aggregate
.. automethod:: cognite.client._api.events.EventsAPI.aggregate_unique_values

Search for events
^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.search

Create events
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.create

Delete events
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.delete

Update events
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.events.EventsAPI.update

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.events
    :members:
    :show-inheritance:


Data sets
---------
Retrieve an data set by id
^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.data_sets.DataSetsAPI.retrieve

Retrieve multiple data sets by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.data_sets.DataSetsAPI.retrieve_multiple

List data sets
^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.data_sets.DataSetsAPI.list

Aggregate data sets
^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.data_sets.DataSetsAPI.aggregate

Create data sets
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.data_sets.DataSetsAPI.create

Delete data sets
^^^^^^^^^^^^^^^^
This functionality is not yet available in the API.

Update data sets
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.data_sets.DataSetsAPI.update

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.data_sets
    :members:
    :show-inheritance:


Files
-----
Retrieve file metadata by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.retrieve

Retrieve multiple files' metadata by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.retrieve_multiple

List files metadata
^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.list

Aggregate files metadata
^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.aggregate

Search for files
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.search

Create file metadata
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.create

Upload a file or directory
^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.upload

Upload a string or bytes
^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.upload_bytes

Retrieve download urls
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.retrieve_download_urls

Download files to disk
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.download

Download a single file to a specific path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.download_to_path

Download a file as bytes
^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.download_bytes

Delete files
^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.delete

Update files metadata
^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.files.FilesAPI.update

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.files
    :members:
    :show-inheritance:

Functions
---------

Create function
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.functions.FunctionsAPI.create

Delete function
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.functions.FunctionsAPI.delete

List functions
^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.functions.FunctionsAPI.list

Retrieve function
^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.functions.FunctionsAPI.retrieve

Retrieve multiple functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.functions.FunctionsAPI.retrieve_multiple

Call function
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.functions.FunctionsAPI.call


Function calls
^^^^^^^^^^^^^^
List function calls
~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.functions.FunctionCallsAPI.list

Retrieve function call
~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.functions.FunctionCallsAPI.retrieve

Retrieve function call response
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.functions.FunctionCallsAPI.get_response

Retrieve function call logs
~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.functions.FunctionCallsAPI.get_logs

Function schedules
^^^^^^^^^^^^^^^^^^
List function schedules
~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.functions.FunctionSchedulesAPI.list

Create function schedule
~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.functions.FunctionSchedulesAPI.create

Delete function schedule
~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.functions.FunctionSchedulesAPI.delete

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.functions
    :members:
    :show-inheritance:

Time series
-----------
Retrieve a time series by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.retrieve

Retrieve multiple time series by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.retrieve_multiple

List time series
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.list

Aggregate time series
^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.aggregate

Search for time series
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.search

Create time series
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.create

Delete time series
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.delete

Update time series
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.time_series.TimeSeriesAPI.update

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.time_series
    :members:
    :show-inheritance:


Synthetic time series
---------------------

Calculate the result of a function on time series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.synthetic_time_series.SyntheticDatapointsAPI.query

Data points
-----------
Retrieve datapoints
^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.retrieve

Retrieve datapoints as numpy arrays
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.retrieve_arrays

Retrieve datapoints in pandas dataframe
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.retrieve_dataframe

Retrieve datapoints in time zone in pandas dataframe
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.retrieve_dataframe_in_tz

Retrieve latest datapoint
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.retrieve_latest

Insert data points
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.insert

Insert data points into multiple time series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.insert_multiple

Insert pandas dataframe
^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.insert_dataframe

Delete a range of data points
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.delete_range

Delete ranges of data points
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.datapoints.DatapointsAPI.delete_ranges


Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.datapoints
    :members:
    :show-inheritance:

Sequences
---------

Retrieve a sequence by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.retrieve

Retrieve multiple sequences by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.retrieve_multiple

List sequences
^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.list

Aggregate sequences
^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.aggregate

Search for sequences
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.search

Create a sequence
^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.create

Delete sequences
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.delete

Update sequences
^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesAPI.update

Retrieve data
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesDataAPI.retrieve

Retrieve pandas dataframe
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesDataAPI.retrieve_dataframe

Insert rows into a sequence
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesDataAPI.insert

Insert a pandas dataframe into a sequence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesDataAPI.insert_dataframe

Delete rows from a sequence
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesDataAPI.delete

Delete a range of rows from a sequence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.sequences.SequencesDataAPI.delete_range

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.sequences
    :members:
    :show-inheritance:
    :exclude-members: Sequence

    .. autoclass:: Sequence
        :noindex:

Raw
---
Databases
^^^^^^^^^
List databases
~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawDatabasesAPI.list

Create new databases
~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawDatabasesAPI.create

Delete databases
~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawDatabasesAPI.delete


Tables
^^^^^^
List tables in a database
~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawTablesAPI.list

Create new tables in a database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawTablesAPI.create

Delete tables from a database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawTablesAPI.delete


Rows
^^^^
Get a row from a table
~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawRowsAPI.retrieve

List rows in a table
~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawRowsAPI.list

Insert rows into a table
~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawRowsAPI.insert

Delete rows from a table
~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawRowsAPI.delete

Retrieve pandas dataframe
~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawRowsAPI.retrieve_dataframe

Insert pandas dataframe
~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.raw.RawRowsAPI.insert_dataframe


Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.raw
    :members:
    :show-inheritance:

Relationships
-------------
Retrieve a relationship by external id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.relationships.RelationshipsAPI.retrieve

Retrieve multiple relationships by external id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.relationships.RelationshipsAPI.retrieve_multiple

List relationships
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.relationships.RelationshipsAPI.list

Create a relationship
^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.relationships.RelationshipsAPI.create

Update relationships
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.relationships.RelationshipsAPI.update

Delete relationships
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.relationships.RelationshipsAPI.delete

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.relationships
    :members:
    :show-inheritance:

Geospatial
----------
.. note::
   Check https://github.com/cognitedata/geospatial-examples for some complete examples.

Create feature types
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.create_feature_types

Delete feature types
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.delete_feature_types

List feature types
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.list_feature_types

Retrieve feature types
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.retrieve_feature_types

Update feature types
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.patch_feature_types

Create features
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.create_features

Delete features
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.delete_features

Retrieve features
^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.retrieve_features

Update features
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.update_features

List features
^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.list_features

Search features
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.search_features

Stream features
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.stream_features

Aggregate features
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.aggregate_features

Get coordinate reference systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.get_coordinate_reference_systems

List coordinate reference systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.list_coordinate_reference_systems

Create coordinate reference systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.create_coordinate_reference_systems


Put raster data
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.put_raster

Delete raster data
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.delete_raster

Get raster data
^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.get_raster

Compute
^^^^^^^
.. automethod:: cognite.client._api.geospatial.GeospatialAPI.compute

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.geospatial
    :members:
    :show-inheritance:


3D
--
Models
^^^^^^
Retrieve a model by ID
~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDModelsAPI.retrieve

List models
~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDModelsAPI.list

Create models
~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDModelsAPI.create

Update models
~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDModelsAPI.update

Delete models
~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDModelsAPI.delete


Revisions
^^^^^^^^^
Retrieve a revision by ID
~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.retrieve

Create a revision
~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.create

List revisions
~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.list

Update revisions
~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.update

Delete revisions
~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.delete

Update a revision thumbnail
~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.update_thumbnail

List nodes
~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.list_nodes

Filter nodes
~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.filter_nodes

List ancestor nodes
~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.list_ancestor_nodes


Files
^^^^^
Retrieve a 3D file
~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDFilesAPI.retrieve

Asset mappings
^^^^^^^^^^^^^^
Create an asset mapping
~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDAssetMappingAPI.create

List asset mappings
~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDAssetMappingAPI.list

Delete asset mappings
~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.three_d.ThreeDAssetMappingAPI.delete

..
    Reveal
    ^^^^^^
    Retrieve a revision by ID
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    .. automethod:: cognite.client._api.three_d.ThreeDRevealAPI.retrieve_revision

    List sectors
    ~~~~~~~~~~~~
    .. automethod:: cognite.client._api.three_d.ThreeDRevealAPI.list_sectors

    List nodes
    ~~~~~~~~~~
    .. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.list_nodes

    List ancestor nodes
    ~~~~~~~~~~~~~~~~~~~
    .. automethod:: cognite.client._api.three_d.ThreeDRevisionsAPI.list_ancestor_nodes

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.three_d
    :members:
    :show-inheritance:

Contextualization
-----------------
These APIs will return as soon as possible, deferring a blocking wait until the last moment. Nevertheless, they can block for a long time awaiting results.

Fit Entity Matching Model
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.fit

Re-fit Entity Matching Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.refit

Retrieve Entity Matching Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.retrieve
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.retrieve_multiple
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.list

Delete Entity Matching Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.delete

Update Entity Matching Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.update

Predict Using an Entity Matching Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.entity_matching.EntityMatchingAPI.predict

Detect entities in Engineering Diagrams
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.diagrams.DiagramsAPI.detect

Convert to an interactive SVG where the provided annotations are highlighted
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.diagrams.DiagramsAPI.convert



Vision
^^^^^^

The Vision API enable extraction of information from imagery data based on
their visual content. For example, you can can extract features such as text, asset tags or industrial objects from images using this service.

**Quickstart**

Start an asynchronous job to extract information from image files stored in CDF:

.. code:: python

    from cognite.client import CogniteClient
    from cognite.client.data_classes.contextualization import VisionFeature

    c = CogniteClient()
    extract_job = c.vision.extract(
        features=[VisionFeature.ASSET_TAG_DETECTION, VisionFeature.PEOPLE_DETECTION],
        file_ids=[1, 2],
    )


The returned job object, :code:`extract_job`, can be used to retrieve the status of the job and the prediction results once the job is completed.
Wait for job completion and get the parsed results:

.. code:: python

    extract_job.wait_for_completion()
    for item in extract_job.items:
        predictions = item.predictions
        # do something with the predictions

Save the prediction results in CDF as `Annotations <https://docs.cognite.com/api/v1/#tag/Annotations>`_:

.. code:: python

    extract_job.save_predictions()

.. note::
    Prediction results are stored in CDF as `Annotations <https://docs.cognite.com/api/v1/#tag/Annotations>`_ using the :code:`images.*` annotation types. In particular, text detections are stored as :code:`images.TextRegion`, asset tag detections are stored as :code:`images.AssetLink`, while other detections are stored as :code:`images.ObjectDetection`.

Tweaking the parameters of a feature extractor:

.. code:: python

    from cognite.client.data_classes.contextualization import FeatureParameters, TextDetectionParameters

    extract_job = c.vision.extract(
        features=VisionFeature.TEXT_DETECTION,
        file_ids=[1, 2],
        parameters=FeatureParameters(text_detection_parameters=TextDetectionParameters(threshold=0.9))
    )

Extract
~~~~~~~

.. automethod:: cognite.client._api.vision.VisionAPI.extract

Get vision extract job
~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: cognite.client._api.vision.VisionAPI.get_extract_job


Contextualization Data Classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.contextualization
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:


.. automodule:: cognite.client.data_classes.annotation_types.images
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:


.. automodule:: cognite.client.data_classes.annotation_types.primitives
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:


Templates
---------
Create Template groups
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupsAPI.create

Upsert Template groups
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupsAPI.upsert

Retrieve Template groups
^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupsAPI.retrieve_multiple

List Template groups
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupsAPI.list

Delete Template groups
^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupsAPI.delete

Upsert a Template group version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupVersionsAPI.upsert

List Temple Group versions
^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupVersionsAPI.list

Delete a Temple Group version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateGroupVersionsAPI.delete

Run a GraphQL query
^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplatesAPI.graphql_query

Create Template instances
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateInstancesAPI.create

Upsert Template instances
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateInstancesAPI.upsert

Update Template instances
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateInstancesAPI.update

Retrieve Template instances
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateInstancesAPI.retrieve_multiple

List Template instances
^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateInstancesAPI.list

Delete Template instances
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateInstancesAPI.delete

Create Views
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateViewsAPI.create

Upsert Views
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateViewsAPI.upsert

List Views
^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateViewsAPI.list

Resolve View
^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateViewsAPI.resolve

Delete Views
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.templates.TemplateViewsAPI.delete

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.templates
    :members:
    :show-inheritance:

Annotations
-----------

Retrieve an annotation by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.annotations.AnnotationsAPI.retrieve

Retrieve multiple annotations by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.annotations.AnnotationsAPI.retrieve_multiple

List annotation
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.annotations.AnnotationsAPI.list

Create an annotation
^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.annotations.AnnotationsAPI.create

Suggest an annotation
^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.annotations.AnnotationsAPI.suggest

Update annotations
^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.annotations.AnnotationsAPI.update

Delete annotations
^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.annotations.AnnotationsAPI.delete

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.annotations
    :members:
    :show-inheritance:

Identity and access management
------------------------------
Tokens
^^^^^^
Inspect the token currently used by the client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.TokenAPI.inspect

Groups
^^^^^^
List groups
~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.GroupsAPI.list

Create groups
~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.GroupsAPI.create

Delete groups
~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.GroupsAPI.delete


Security categories
^^^^^^^^^^^^^^^^^^^
List security categories
~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.SecurityCategoriesAPI.list

Create security categories
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.SecurityCategoriesAPI.create

Delete security categories
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.SecurityCategoriesAPI.delete


Sessions
^^^^^^^^^^^^^^^^^^^
List sessions
~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.SessionsAPI.list

Create a session
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.SessionsAPI.create

Revoke a session
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.iam.SessionsAPI.revoke


Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.iam
    :members:
    :show-inheritance:


Extraction pipelines
--------------------
List extraction pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelinesAPI.list

Create extraction pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelinesAPI.create

Retrieve an extraction pipeline by ID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelinesAPI.retrieve

Retrieve multiple extraction pipelines by ID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelinesAPI.retrieve_multiple

Update extraction pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelinesAPI.update

Delete extraction pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelinesAPI.delete


Extraction pipeline runs
^^^^^^^^^^^^^^^^^^^^^^^^
List runs for an extraction pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelineRunsAPI.list

Report new runs
~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelineRunsAPI.create


Extraction pipeline configs
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Get the latest or a specific config revision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelineConfigsAPI.retrieve

List configuration revisions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelineConfigsAPI.list

Create a config revision
~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelineConfigsAPI.create

Revert to an earlier config revision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.extractionpipelines.ExtractionPipelineConfigsAPI.revert

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.extractionpipelines
    :members:
    :show-inheritance:


Transformations
------------------------

Create transformations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.create

Retrieve transformations by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.retrieve

.. automethod:: cognite.client._api.transformations.TransformationsAPI.retrieve_multiple

Run transformations by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.run
.. automethod:: cognite.client._api.transformations.TransformationsAPI.run_async

Preview transformations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.preview

Cancel transformation run by id
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.cancel

List transformations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.list

Update transformations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.update

Delete transformations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automethod:: cognite.client._api.transformations.TransformationsAPI.delete

Transformation Schedules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create transformation Schedules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.schedules.TransformationSchedulesAPI.create

Retrieve transformation schedules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.schedules.TransformationSchedulesAPI.retrieve

Retrieve multiple transformation schedules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.schedules.TransformationSchedulesAPI.retrieve_multiple

List transformation schedules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.schedules.TransformationSchedulesAPI.list

Update transformation schedules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.schedules.TransformationSchedulesAPI.update

Delete transformation schedules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.schedules.TransformationSchedulesAPI.delete

Transformation Notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create transformation notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.notifications.TransformationNotificationsAPI.create

List transformation notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.notifications.TransformationNotificationsAPI.list

Delete transformation notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.notifications.TransformationNotificationsAPI.delete

Transformation Jobs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Retrieve transformation jobs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.jobs.TransformationJobsAPI.retrieve

.. automethod:: cognite.client._api.transformations.jobs.TransformationJobsAPI.retrieve_multiple

List transformation jobs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.jobs.TransformationJobsAPI.list

Transformation Schema
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get transformation schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automethod:: cognite.client._api.transformations.schema.TransformationSchemaAPI.retrieve

Data classes
^^^^^^^^^^^^
.. automodule:: cognite.client.data_classes.transformations
    :members:
    :show-inheritance:
.. automodule:: cognite.client.data_classes.transformations.schedules
    :members:
    :show-inheritance:
.. automodule:: cognite.client.data_classes.transformations.notifications
    :members:
    :show-inheritance:
.. automodule:: cognite.client.data_classes.transformations.jobs
    :members:
    :show-inheritance:
.. automodule:: cognite.client.data_classes.transformations.schema
    :members:
    :show-inheritance:
.. automodule:: cognite.client.data_classes.transformations.common
    :members:
    :show-inheritance:


Base data classes
-----------------
CogniteResource
^^^^^^^^^^^^^^^
.. autoclass:: cognite.client.data_classes._base.CogniteResource
    :members:

CogniteResourceList
^^^^^^^^^^^^^^^^^^^
.. autoclass:: cognite.client.data_classes._base.CogniteResourceList
    :members:

CogniteResponse
^^^^^^^^^^^^^^^
.. autoclass:: cognite.client.data_classes._base.CogniteResponse
    :members:

CogniteFilter
^^^^^^^^^^^^^
.. autoclass:: cognite.client.data_classes._base.CogniteFilter
    :members:

CogniteUpdate
^^^^^^^^^^^^^
.. autoclass:: cognite.client.data_classes._base.CogniteUpdate
    :members:

Exceptions
----------
CogniteAPIError
^^^^^^^^^^^^^^^
.. autoexception:: cognite.client.exceptions.CogniteAPIError

CogniteNotFoundError
^^^^^^^^^^^^^^^^^^^^
.. autoexception:: cognite.client.exceptions.CogniteNotFoundError

CogniteDuplicatedError
^^^^^^^^^^^^^^^^^^^^^^
.. autoexception:: cognite.client.exceptions.CogniteDuplicatedError

CogniteImportError
^^^^^^^^^^^^^^^^^^
.. autoexception:: cognite.client.exceptions.CogniteImportError

CogniteMissingClientError
^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoexception:: cognite.client.exceptions.CogniteMissingClientError


Utils
-----
Convert timestamp to milliseconds since epoch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: cognite.client.utils.timestamp_to_ms

Convert milliseconds since epoch to datetime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: cognite.client.utils.ms_to_datetime

Convert datetime to milliseconds since epoch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: cognite.client.utils.datetime_to_ms

Testing
-------
Object to use as a mock for CogniteClient
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: cognite.client.testing.CogniteClientMock

Use a context manager to monkeypatch CogniteClient
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: cognite.client.testing.monkeypatch_cognite_client
