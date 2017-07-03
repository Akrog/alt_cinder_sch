# Copyright (c) 2017 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from cinder.scheduler import host_manager
from oslo_log import log as logging
from oslo_utils import timeutils


LOG = logging.getLogger(__name__)


# In newer Cinder versions it's called BackendState, but in older ones it's
# HostState
BaseStateClass = getattr(host_manager, 'BackendState',
                         getattr(host_manager, 'HostState', None))


def get_over_subscription(self, filter_properties, default_thin=True):
    # If type's extra specs doesn't declare provisioning type use default
    thin = default_thin

    # Get provisioning type considering filter_properties could be None
    vol_type = (filter_properties or {}).get('volume_type', {}) or {}
    req_type = vol_type.get('extra_specs', {}).get('provisioning:type')

    # Ignore non thin or thick values for the provisioning type
    if req_type in ('thin', 'thick'):
        thin = req_type == 'thin'

    # Default and requested are only relevant if backend supports it
    if thin:
        thin = self.thin_provisioning_support
    else:
        thin = not self.thick_provisioning_support

    if thin:
        return float(self.max_over_subscription_ratio)
    return 1.0


def consume_from_volume(self, volume, filter_properties=None):
    """Incrementally update host state from a volume."""
    volume_gb = volume['size']
    self.allocated_capacity_gb += volume_gb
    self.provisioned_capacity_gb += volume_gb
    if self.free_capacity_gb not in ('infinite', 'unknown'):
        over_subscription = self.get_over_subscription(filter_properties)
        consume = volume_gb / over_subscription
        LOG.debug('Consuming %sGB/%sGB from %s', consume,
                  self.free_capacity_gb, self.host)
        self.free_capacity_gb -= consume
    self.updated = timeutils.utcnow()


def backend_id(self):
    return getattr(self, 'cluster_name', None) or self.host


class BackendStateThin(BaseStateClass):
    default_thin = True

    get_over_subscription = get_over_subscription
    consume_from_volume = consume_from_volume

    backend_id = property(backend_id)


class BackendStateThick(BackendStateThin):
    default_thin = False


class HostManagerThin(host_manager.HostManager):
    backend_state_cls = BackendStateThin
    host_state_cls = backend_state_cls

    def __init__(self, *args, **kwargs):
        # Since we have no mechanism in Cinder to configure the Pool class to
        # use we forcefully replace the original methods in the class with our
        # own
        host_manager.PoolState.get_over_subscription = get_over_subscription
        host_manager.PoolState.consume_from_volume = consume_from_volume
        host_manager.PoolState.default_thin = (
            self.backend_state_cls.default_thin)
        super(HostManagerThin, self).__init__(*args, **kwargs)
        # Our scheduler driver is expecting to have backend_id property
        if not hasattr(host_manager.PoolState, 'backend_id'):
            # If not present simulate pointing to the host value
            host_manager.PoolState.backend_id = property(backend_id)


class HostManagerThick(HostManagerThin):
    backend_state_cls = BackendStateThick
    host_state_cls = backend_state_cls
