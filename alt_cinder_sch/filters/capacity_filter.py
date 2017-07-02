# Copyright (c) 2012 Intel
# Copyright (c) 2012 OpenStack Foundation
# Copyright (c) 2015 EMC Corporation
# Copyright (c) 2017 Red Hat, Inc.
#
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


import math

from cinder import exception
from cinder.scheduler import filters
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class AltCapacityFilter(filters.BaseBackendFilter):
    """Capacity filters based on volume backend's capacity utilization.

    This requires using HostManagerThin or HostManagerThick."""

    def _get_grouping(self, backend_state):
        return 'cluster' if backend_state.cluster_name else 'host'

    def _check_valid_backend_state(self, backend_state, filter_properties):
        if not hasattr(backend_state, 'get_over_subscription'):
            raise exception.InvalidParameterValue(
                'scheduler_host_manager must be HostManagerThin or '
                'HostManagerThick, not %s.' % type(backend_state))

        if backend_state.free_capacity_gb is None:
            # Fail Safe
            LOG.error("Free capacity not set: "
                      "volume node info collection broken.")
            return False

        over_subscription = backend_state.get_over_subscription(
            filter_properties)
        if over_subscription < 1.0:
            LOG.warning("Filtering out %(grouping)s %(grouping_name)s "
                        "with an invalid maximum over subscription ratio "
                        "of %(oversub_ratio).2f. The ratio should be a "
                        "minimum of 1.0.",
                        {"oversub_ratio":
                            over_subscription,
                         "grouping": self._get_grouping(backend_state),
                         "grouping_name": backend_state.backend_id})
            return False
        return True

    def backend_passes(self, backend_state, filter_properties):
        """Return True if host has sufficient capacity."""

        if not self._check_valid_backend_state(backend_state,
                                               filter_properties):
            return False

        volid = None
        # If the volume already exists on this host, don't fail it for
        # insufficient capacity (e.g., if we are retyping)
        if backend_state.backend_id == filter_properties.get('vol_exists_on'):
            return True

        spec = filter_properties.get('request_spec')
        if spec:
            volid = spec.get('volume_id')

        if filter_properties.get('new_size'):
            # If new_size is passed, we are allocating space to extend a volume
            requested_size = (int(filter_properties.get('new_size')) -
                              int(filter_properties.get('size')))
            action = 'extend'
        else:
            requested_size = filter_properties.get('size')
            action = 'create'

        LOG.debug('Checking if %(grouping)s %(grouping_name)s can %(action)s '
                  'a %(size)s GB volume (%(id)s)',
                  {'grouping': self._get_grouping(backend_state),
                   'action': action,
                   'grouping_name': backend_state.backend_id, 'id': volid,
                   'size': requested_size})

        # requested_size is 0 means that it's a manage request.
        if requested_size == 0:
            return True

        return self._fits(backend_state, filter_properties, requested_size)

    def _fits(self, backend_state, filter_properties, requested_size):
        over_subscription = backend_state.get_over_subscription(
            filter_properties)
        free_space = backend_state.free_capacity_gb
        total_space = backend_state.total_capacity_gb
        reserved = float(backend_state.reserved_percentage) / 100
        if free_space in ('infinite', 'unknown'):
            # NOTE(zhiteng) for those back-ends cannot report actual
            # available capacity, we assume it is able to serve the
            # request.  Even if it was not, the retry mechanism is
            # able to handle the failure by rescheduling
            return True
        elif total_space in ('infinite', 'unknown'):
            # If total_space is 'infinite' or 'unknown' and reserved
            # is 0, we assume the back-ends can serve the request.
            # If total_space is 'infinite' or 'unknown' and reserved
            # is not 0, we cannot calculate the reserved space.
            # float(total_space) will throw an exception. total*reserved
            # also won't work. So the back-ends cannot serve the request.
            return reserved == 0
        total = float(total_space)

        grouping = self._get_grouping(backend_state)
        if total <= 0:
            LOG.warning("Insufficient free space for volume creation. "
                        "Total capacity is %(total).2f on %(grouping)s "
                        "%(grouping_name)s.",
                        {"total": total,
                         "grouping": grouping,
                         "grouping_name": backend_state.backend_id})
            return False

        # Calculate how much free space is left after taking into account
        # the reserved space.
        free = free_space - math.floor(total * reserved)

        # Only evaluate using max_over_subscription_ratio if
        # thin_provisioning_support is True. Check if the ratio of
        # provisioned capacity over total capacity has exceeded over
        # subscription ratio.
        if over_subscription >= 1:
            provisioned_ratio = ((backend_state.provisioned_capacity_gb +
                                  requested_size) / total)
            if provisioned_ratio > over_subscription:
                msg_args = {
                    "provisioned_ratio": provisioned_ratio,
                    "oversub_ratio": over_subscription,
                    "grouping": grouping,
                    "grouping_name": backend_state.backend_id,
                }
                LOG.warning(
                    "Insufficient free space for thin provisioning. "
                    "The ratio of provisioned capacity over total capacity "
                    "%(provisioned_ratio).2f has exceeded the maximum over "
                    "subscription ratio %(oversub_ratio).2f on %(grouping)s "
                    "%(grouping_name)s.", msg_args)
                return False
            else:
                # Thin provisioning is enabled and projected over-subscription
                # ratio does not exceed max_over_subscription_ratio. The host
                # passes if "adjusted" free virtual capacity is enough to
                # accommodate the volume. Adjusted free virtual capacity is
                # the currently available free capacity (taking into account
                # of reserved space) which we can over-subscribe.
                adjusted_free_virtual = free * over_subscription
                return adjusted_free_virtual >= requested_size

        msg_args = {"grouping_name": backend_state.backend_id,
                    "grouping": grouping,
                    "requested": requested_size,
                    "available": free}

        if free < requested_size:
            LOG.warning("Insufficient free space for volume creation "
                        "on %(grouping)s %(grouping_name)s (requested / "
                        "avail): %(requested)s/%(available)s",
                        msg_args)
            return False

        LOG.debug("Space information for volume creation "
                  "on %(grouping)s %(grouping_name)s (requested / avail): "
                  "%(requested)s/%(available)s", msg_args)
        return True
