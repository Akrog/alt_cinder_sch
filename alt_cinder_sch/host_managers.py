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
from oslo_utils import timeutils


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

    # Default and requested Thin is only relevant if backend supports thin
    thin = thin and self.thin_provisioning_support

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
        self.free_capacity_gb -= volume_gb / over_subscription
    self.updated = timeutils.utcnow()


class BackendStateThin(BaseStateClass):
    default_thin = True

    get_over_subscription = get_over_subscription
    consume_from_volume = consume_from_volume


class BackendStateThick(BackendStateThin):
    default_thin = False


class HostManagerThin(host_manager.HostManager):
    backend_state_cls = BackendStateThin

    def __init__(self, *args, **kwargs):
        # Since we have no mechanism in Cinder to configure the Pool class to
        # use we forcefully replace the original methods in the class with our
        # own
        host_manager.PoolState.get_over_subscription = get_over_subscription
        host_manager.PoolState.consume_from_volume = consume_from_volume
        host_manager.PoolState.default_thin = (
            self.backend_state_cls.default_thin)
        super(HostManagerThin, self).__init__(*args, **kwargs)


class HostManagerThick(HostManagerThin):
    backend_state_cls = BackendStateThick
