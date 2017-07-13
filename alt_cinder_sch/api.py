from cinder import db
from cinder import exception
from cinder.volume import api
from cinder.volume import volume_types
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

    def _image_has_valid_volume_type(self, context, image_id):
        if not image_id:
            return False

        image = self.image_service.show(context, image_id)
        # check whether image is active
        type_name = image.get('properties', {}).get('cinder_img_volume_type')

        if not type_name:
            return False

        try:
            volume_types.get_volume_type_by_name(context, type_name)
            return True
        except exception.VolumeTypeNotFoundByName:
            return False

    def create(self, context, size, name, description, snapshot=None,
               image_id=None, volume_type=None, metadata=None,
               availability_zone=None, source_volume=None,
               *args, **kwargs):
        """Create a volume with configurable default volume types.

        Use extra information from Keystone to retrieve project and user's
        default volume type values.

        Keystone default volume types can be UUIDs or Names.

        Order of preference is:

        1- Source volume type: volume, snapshot, image metadata
        2- If Keystone's user has default_vol_type in extra field.
        3- If Keystone's project has default_vol_type in extra field.
        4- Cinder configured `default_volume_type`
        """
        # Check Keystone's default volume types when user didn't specify it
        # explicitly, via source volume, snapshot, or in the image metadata.
        if not (volume_type or source_volume or snapshot or
                self._image_has_valid_volume_type(context, image_id)):
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
            image_id=image_id, volume_type=volume_type, metadata=metadata,
            availability_zone=availability_zone, source_volume=source_volume,
            *args, **kwargs)
