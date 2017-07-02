Alternative Cinder Scheduler Classes
====================================

.. image:: https://img.shields.io/pypi/v/alt_cinder_sch.svg
   :target: https://pypi.python.org/pypi/alt_cinder_sch

.. image:: https://readthedocs.org/projects/alt-cinder-sch/badge/?version=latest
   :target: https://alt-cinder-sch.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://img.shields.io/pypi/pyversions/alt_cinder_sch.svg
   :target: https://pypi.python.org/pypi/alt_cinder_sch

.. image:: https://pyup.io/repos/github/akrog/alt_cinder_sch/shield.svg
     :target: https://pyup.io/repos/github/akrog/alt_cinder_sch/
     :alt: Updates

.. image:: https://img.shields.io/:license-apache-blue.svg
   :target: http://www.apache.org/licenses/LICENSE-2.0


Alternative Classes such as filters, host managers, etc. for Cinder, the
OpenStack Block Storage service.

The main purpose of this library is to illustrate the broad range of
possibilities of the Cinder Scheduler provided by its flexible mechanisms.

Currently there's only 2 interesting features, which are the possibility of
changing the default provisioning type on volume creation for volumes that
don't specify the type using the `provisioning:type` extra spec and an
alternative calculation of the free space consumption.

Scheduler's original approach to space consumption by new volumes is
conservative to prevent backends from filling up due to a sudden burst of
volume creations.

The alternative approach is more aggressive and is adequate for deployments
where the workload is well know and a lot of thin volumes could be requested
at the same time.

It's important to notice that even though the Schedulers will be able to
understand `provisioining:type` extra spec it will depend on the backend if
this parameter is actually used or not.

* Free software: Apache Software License 2.0
* Documentation: https://alt-cinder-sch.readthedocs.io.

Features
--------

* Can default capacity calculations to thin or thick.
* Less conservative approach to free space consumption calculations.


Usage
-----

First we'll need to have the package installed:

.. code-block:: console

 # pip install alt_cinder-sch

Then we'll have to configure Cinder's schedulers to use the package::

    scheduler_host_manager = alt_cinder_sch.host_managers.HostManagerThin
    scheduler_default_filters = AvailabilityZoneFilter,AltCapacityFilter,CapabilitiesFilter
    scheduler_driver = alt_cinder_sch.scheduler_drivers.FilterScheduler

And finally restart scheduler services.
