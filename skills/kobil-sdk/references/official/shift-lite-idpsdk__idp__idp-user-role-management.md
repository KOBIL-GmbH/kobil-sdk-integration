> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-user-role-management> on 2026-09-28. Converted to Markdown; wording unchanged.

# User Role Management

User Role Management allows applications to provide access and permissions through roles, ensuring consistency among users. Roles include **admin**, **manager**, **employee**, and **user roles**,, with various permissions such as Create-Client, Impersonation, Manage-authorization, etc.

### Super Admin Access

* When admin role is assigned to a user in the Master Tenant, they become a Super Admin.
* Super Admins have access to manage the entire IDP.

For information on granting Admin role to a user for multiple tenants from the Master Tenant, refer to the [User Role Management Documentation](https://developer.kobil.com/docs/idp-docs/administration/userrolemanagement/#how-to-assign-admin-role).

### Admin Access

Admin Access grants a user admin privileges for a specific tenant. Admin Access can be set for a Tenant’s User in two ways:

* For information on granting Admin Access to a user for multiple tenants from the Master Tenant, refer to the [Admin Access for Multiple Tenants](https://developer.kobil.com/docs/idp-docs/administration/userrolemanagement/#1-multiple-tenant-access-can-be-given-to-the-user-from-the-master-tenant).
* To provide Admin Access from a specific tenant, follow the steps outlined in the [Admin Access from Specific Tenant](https://developer.kobil.com/docs/idp-docs/administration/userrolemanagement#2-admin-access-can-be-given-from-the-specific-tenant)

### Example Roles

1. **Developer Role:**

   * View and Manage access for users.
   * Permissions: View-authorization, View-clients, Manage-users, Create-clients, etc.
2. **Help Desk:**

   * Read-only access in the Tenant.
   * Permissions: View-authorization, View-clients, View-users, etc.

For detailed instructions, refer to the full [User Role Management documentation](https://developer.kobil.com/docs/idp-docs/administration/userrolemanagement/#composite-roles).
