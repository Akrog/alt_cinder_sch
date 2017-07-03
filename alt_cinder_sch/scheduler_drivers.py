# Copyright (c) 2011 Intel Corporation
# Copyright (c) 2011 OpenStack Foundation
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


from cinder import exception
from cinder.i18n import _
from cinder.scheduler import filter_scheduler
from cinder.volume import utils
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


# In newer Cinder versions it's called NoValidBackend, but in older ones it's
# NoValidHost
NoValidBackend = getattr(exception, 'NoValidBackend',
                         getattr(exception, 'NoValidHost', None))


class FilterScheduler(filter_scheduler.FilterScheduler):
    """Like Cinder's default but passing filter_properties to consume."""

    def _choose_top_backend(self, weighed_backends, request_spec,
                            filter_properties=None):
        top_backend = weighed_backends[0]
        backend_state = top_backend.obj
        LOG.debug("Choosing %s", backend_state.backend_id)
        volume_properties = request_spec['volume_properties']
        # Standard BackendState/HostSate doesn't accept filter_properties
        try:
            backend_state.consume_from_volume(volume_properties,
                                              filter_properties)
        except TypeError:
            backend_state.consume_from_volume(volume_properties)
        return top_backend

    def find_retype_backend(self, context, request_spec,
                            filter_properties=None, migration_policy='never'):
        """Find a backend that can accept the volume with its new type."""
        filter_properties = filter_properties or {}
        backend = (request_spec['volume_properties'].get('cluster_name') or
                   request_spec['volume_properties']['host'])

        # The volume already exists on this backend, and so we shouldn't check
        # if it can accept the volume again in the CapacityFilter.
        filter_properties['vol_exists_on'] = backend
        weighed_backends = self._get_weighted_candidates(context, request_spec,
                                                         filter_properties)
        if not weighed_backends:
            raise NoValidBackend(
                reason=_('No valid backends for volume %(id)s with type '
                         '%(type)s') % {'id': request_spec['volume_id'],
                                        'type': request_spec['volume_type']})

        for weighed_backend in weighed_backends:
            backend_state = weighed_backend.obj
            if backend_state.backend_id == backend:
                return backend_state

        if utils.extract_host(backend, 'pool') is None:
            # legacy volumes created before pool is introduced has no pool
            # info in host.  But host_state.host always include pool level
            # info. In this case if above exact match didn't work out, we
            # find host_state that are of the same host of volume being
            # retyped. In other words, for legacy volumes, retyping could
            # cause migration between pools on same host, which we consider
            # it is different from migration between hosts thus allow that
            # to happen even migration policy is 'never'.
            for weighed_backend in weighed_backends:
                backend_state = weighed_backend.obj
                new_backend = utils.extract_host(backend_state.backend_id,
                                                 'backend')
                if new_backend == backend:
                    return backend_state

        if migration_policy == 'never':
            raise NoValidBackend(
                reason=_('Current backend not valid for volume %(id)s with '
                         'type %(type)s, migration not allowed') %
                {'id': request_spec['volume_id'],
                 'type': request_spec['volume_type']})

        top_backend = self._choose_top_backend(weighed_backends, request_spec,
                                               filter_properties)
        return top_backend.obj

    def _schedule(self, context, request_spec, filter_properties=None):
        weighed_backends = self._get_weighted_candidates(context, request_spec,
                                                         filter_properties)
        # When we get the weighed_backends, we clear those backends that don't
        # match the group's backend.
        group_backend = request_spec.get('group_backend')
        if weighed_backends and group_backend:
            # Get host name including host@backend#pool info from
            # weighed_backends.
            for backend in weighed_backends[::-1]:
                backend_id = utils.extract_host(backend.obj.backend_id)
                if backend_id != group_backend:
                    weighed_backends.remove(backend)
        if not weighed_backends:
            LOG.warning('No weighed backend found for volume '
                        'with properties: %s',
                        filter_properties['request_spec'].get('volume_type'))
            return None
        return self._choose_top_backend(weighed_backends, request_spec,
                                        filter_properties)

    # For compatibility with older Cinder services
    _choose_top_host = _choose_top_backend
    find_retype_host = find_retype_backend
