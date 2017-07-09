=====
Usage
=====

Proportional Free Space Calculation
-----------------------------------

To use Alternative Cinder Scheduler Classes in a Cinder deployment the package
will need to be first installed in all scheduler nodes as instructed in the
:doc:`installation guide <installation>`.

Then configuration files will need to be updated to use the classes::

    scheduler_host_manager = alt_cinder_sch.host_managers.HostManagerThin
    scheduler_default_filters = AvailabilityZoneFilter,AltCapacityFilter,CapabilitiesFilter
    scheduler_driver = alt_cinder_sch.scheduler_drivers.FilterScheduler

Scheduler's default filters could vary depending on your configuration, but
the only filter provided by this package at the moment is the
AltCapacityFilter.

In above example we were defaulting to thin provisioning calculations for any
backend that supported thin provisioning, but we can also default to thick
provisioning  is we use `HostManagerThick` instead as the
`scheduler_default_filters`.


Default Volume Types
--------------------

To support Default Volume Types based on users or projects the package needs to
be installed in all API nodes as instructed in the
:doc:`installation guide <installation>`.

Then configuration files will need to be updated to use the API class::

    volume_api_class = alt_cinder_sch.api.DefaultVolumeTypeAPI

And the default volume type will need to be added to the users and/or projects
in Keystone directly in the DB (there's no REST API).

Data must be added to extra DB field as JSON with key `default_vol_type`.

If there is no data in the user's extra field we can run::

    UPDATE user
    SET extra='{"default_vol_type": "iscsi"}'
    WHERE id=$USER_UUID;

If the project's extra field already had info, like an email, we could do::

    UPDATE project
    SET extra=CONCAT(SUBSTRING(extra, 1, LENGTH(extra) - 1),
                     ', "default_vol_type": 'iscsi"}')
    WHERE name='admin';
