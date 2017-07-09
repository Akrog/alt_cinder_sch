from cinder import db
from cinder import exception
from cinder.volume import api
from keystoneauth1 import identity
from keystoneclient import client
from oslo_config import cfg
from oslo_utils import uuidutils


class DefaultVolumeTypeAPI(api.API):
    @staticmethod
    def _get_identity_url(context):
        """Get identity service URL from context or cinder configuration."""
        for service in context.service_catalog:
            if service.get('type') != 'identity':
                continue
            for endpoint in service['endpoints']:
                url = (endpoint.get('internalURL') or
                       endpoint.get('publicURL') or
                       endpoint.get('adminURL'))
                return url
        url = cfg.CONF.keystone_authtoken.auth_uri
        if not url:
            raise exception.CinderException('Indentity service URL could not '
                                            'be found.')
        return url

    @classmethod
    def _get_keystone_client(cls, context):
        """Get a keystone client using context's info and token."""
        url = cls._get_identity_url(context)
        auth = identity.Token(auth_url=url,
                              token=context.auth_token,
                              project_name=context.project_name,
                              project_domain_id=context.project_domain)
        ks = client.Client(auth_url=url, auth=auth)
        return ks

    def create(self, context, size, name, description, snapshot=None,
               image_id=None, volume_type=None, *args, **kwargs):
        """Create a volume with configurable default volume types.

        Use extra information from Keystone to retrieve project and user's
        default volume type values.

        Keystone default volume types can be UUIDs or Names.

        Order of preference is:

        1- If Keystone's user has default_vol_type in extra field.
        2- If Keystone's project has default_vol_type in extra field.
        3- Cinder's default_volume_type
        """

        # Check Keystone's default volume types when user didn't specify it.
        if not volume_type:
            client = self._get_keystone_client(context)
            user = client.users.get(context.user)
            def_vol_type = getattr(user, 'default_vol_type', None)
            # Check project if there's no default on the user
            if not def_vol_type:
                project = client.projects.get(context.project_id)
                def_vol_type = getattr(project, 'default_vol_type', None)

            # if we have a keystone default, retrieve the volume type from db
            if def_vol_type:
                # ctxt = context.elevated()
                if uuidutils.is_uuid_like(def_vol_type):
                    volume_type = db.volume_type_get(context, def_vol_type)
                else:
                    volume_type = db.volume_type_get_by_name(context,
                                                             def_vol_type)

        return super(DefaultVolumeTypeAPI, self).create(
            context, size, name, description, snapshot=snapshot,
            image_id=image_id, volume_type=volume_type, *args,
            **kwargs)
