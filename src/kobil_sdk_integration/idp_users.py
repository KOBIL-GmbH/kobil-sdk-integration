"""Typed user lifecycle operations; no password mutation on profile reuse."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .backend import segment, BackendError
from .idp_admin import Admin

class UserProfile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    enabled: bool | None = None
    emailVerified: bool | None = None
    attributes: dict[str, list[str]] | None = None
    requiredActions: list[str] | None = None


def register(mcp):
    @mcp.tool()
    def sdk_idp_user_list(expected_environment: str, realm: str | None = None, search: str | None = None,
                          first: int = 0, max_results: int = 50) -> dict:
        """List users in an explicit realm. Read-only; needs query/view-users. Follow next_offset until complete; returns no passwords. Use the returned UUID for device/activation tools."""
        with Admin(expected_environment, realm) as api:
            return api.page('/users', first, max_results, {'search':search} if search else {})

    @mcp.tool()
    def sdk_idp_user_search(expected_environment: str, realm: str | None = None,
                            username: str | None = None, email: str | None = None,
                            enabled: bool | None = None, exact: bool = True,
                            first: int = 0, max_results: int = 50) -> dict:
        """Search users by username/email/enabled state. Exact matching defaults to true. Read-only, paginated; does not create identities or reset passwords."""
        with Admin(expected_environment, realm) as api:
            params={k:v for k,v in {'username':username,'email':email,'enabled':enabled,'exact':exact}.items() if v is not None}
            return api.page('/users',first,max_results,params)

    @mcp.tool()
    def sdk_idp_user_count(expected_environment: str, realm: str | None = None, search: str | None = None) -> dict:
        """Count users matching an optional search. Read-only realm admin query; count is not a stable pagination snapshot."""
        with Admin(expected_environment,realm) as api:
            return {'count':api.call('GET','/users/count',params={'search':search} if search else {})}

    @mcp.tool()
    def sdk_idp_user_get(expected_environment: str, user_uuid: str | None = None,
                         username: str | None = None, realm: str | None = None) -> dict:
        """Read a user by UUID or exact username (exactly one). Requires view-users. Returns profile metadata; inspect credential metadata and device state separately."""
        if bool(user_uuid)==bool(username):raise ValueError('Provide exactly one user_uuid or username')
        with Admin(expected_environment,realm) as api:
            if user_uuid:return {'user':api.call('GET','/users/'+segment(user_uuid))}
            rows=api.call('GET','/users',params={'username':username,'exact':True,'max':2})
            if not isinstance(rows,list) or len(rows)>1:raise BackendError('User lookup is ambiguous or invalid')
            return {'exists':bool(rows),'user':rows[0] if rows else None}

    @mcp.tool()
    def sdk_idp_user_create(expected_environment: str, profile: UserProfile, realm: str | None = None) -> dict:
        """Create an IDP profile without a password. Requires manage-users. Existing-name conflicts are reported, not overwritten. Follow with explicit group/credential setup if needed."""
        data=profile.model_dump(exclude_unset=True)
        if not data.get('username'):raise ValueError('username is required')
        with Admin(expected_environment,realm) as api:
            api.call('POST','/users',data)
            return {'created':True,'username':data['username'],'next_step':'Resolve UUID with sdk_idp_user_get; no password or group was set implicitly.'}

    @mcp.tool()
    def sdk_idp_user_update(expected_environment: str, user_uuid: str, changes: UserProfile, realm: str | None = None) -> dict:
        """Update only selected profile fields, preserving other fields. Requires manage-users. Never resets a password; attributes supplied replace that attribute map explicitly."""
        with Admin(expected_environment,realm) as api:
            return api.update('/users/'+segment(user_uuid),changes.model_dump(exclude_unset=True),UserProfile.model_fields)

    @mcp.tool()
    def sdk_idp_user_enable(expected_environment: str, user_uuid: str, realm: str | None = None) -> dict:
        """Enable an existing user. Changes availability only; no password/group changes. Requires manage-users."""
        with Admin(expected_environment,realm) as api:return api.update('/users/'+segment(user_uuid),{'enabled':True},{'enabled'})

    @mcp.tool()
    def sdk_idp_user_disable(expected_environment: str, user_uuid: str, realm: str | None = None) -> dict:
        """Disable an existing user without deleting the profile. Requires manage-users; active-session revocation is a separate operation."""
        with Admin(expected_environment,realm) as api:return api.update('/users/'+segment(user_uuid),{'enabled':False},{'enabled'})

    @mcp.tool()
    def sdk_idp_user_delete(expected_environment: str, user_uuid: str, realm: str | None = None) -> dict:
        """Permanently delete the exact user UUID from the selected realm. Requires manage-users; do not substitute a username or use for routine reuse."""
        with Admin(expected_environment,realm) as api:api.call('DELETE','/users/'+segment(user_uuid));return {'deleted':True,'user_uuid':user_uuid}

    @mcp.tool()
    def sdk_idp_user_credentials_list(expected_environment: str, user_uuid: str, realm: str | None = None) -> dict:
        """List credential IDs/types/labels for a user, never credential contents. Read-only; existing passwords cannot be recovered."""
        with Admin(expected_environment,realm) as api:
            rows=api.call('GET','/users/'+segment(user_uuid)+'/credentials')
            if not isinstance(rows,list):raise BackendError('Expected credential metadata list')
            return {'credentials':[{k:r[k] for k in ('id','type','userLabel','createdDate') if k in r} for r in rows if isinstance(r,dict)]}

    @mcp.tool()
    def sdk_idp_user_credential_delete(expected_environment: str, user_uuid: str, credential_id: str, realm: str | None = None) -> dict:
        """Remove one credential by its ID from the selected user. Requires manage-users; may prevent login. Does not delete the profile."""
        with Admin(expected_environment,realm) as api:api.call('DELETE','/users/'+segment(user_uuid)+'/credentials/'+segment(credential_id));return {'deleted':True,'credential_id':credential_id}

    @mcp.tool()
    def sdk_idp_user_required_actions_update(expected_environment: str, user_uuid: str, actions: list[str], realm: str | None = None) -> dict:
        """Replace this user's required-action list (empty clears it). Requires manage-users; does not alter realm-wide defaults or send email."""
        with Admin(expected_environment,realm) as api:return api.update('/users/'+segment(user_uuid),{'requiredActions':actions},{'requiredActions'})

    @mcp.tool()
    def sdk_idp_user_verify_email_send(expected_environment: str, user_uuid: str, realm: str | None = None) -> dict:
        """Send a verification email to the selected user. Communication/write operation requiring explicit user intent and configured realm email; does not mark email verified."""
        with Admin(expected_environment,realm) as api:api.call('PUT','/users/'+segment(user_uuid)+'/send-verify-email');return {'sent':True,'user_uuid':user_uuid}

    @mcp.tool()
    def sdk_idp_user_actions_email_send(expected_environment: str, user_uuid: str, actions: list[str],
                                       lifespan: int = 3600, realm: str | None = None) -> dict:
        """Send an action email for specified required actions. Communication/write; explicit recipient UUID. Lifespan in seconds (60..86400); SMTP delivery is not proven by backend acceptance."""
        if not actions or not 60<=lifespan<=86400:raise ValueError('Provide actions and lifespan 60..86400')
        with Admin(expected_environment,realm) as api:api.call('PUT','/users/'+segment(user_uuid)+'/execute-actions-email',actions,{'lifespan':lifespan});return {'accepted':True,'user_uuid':user_uuid}
