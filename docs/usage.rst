=====
Usage
=====

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
