> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/set-property/property_flags> on 2026-09-28. Converted to Markdown; wording unchanged.

# Property Flags

For each property so called flags may be set to assign different options to a property. Some flag/owner-combinations are not allowed.
Some flags can be grouped together:

APP\_PORTAL\_ACCESS: With this property flags the access to a property from the App and/or from the portal may be restricted. This will be enforced by SDK and SSMS. This flag has the 4 following possible values:

* APP\_PORTAL\_ACCESS\_ALL
* APP\_PORTAL\_ACCESS\_NO\_APP
* APP\_PORTAL\_ACCESS\_NO\_PORTAL
* APP\_PORTAL\_ACCESS\_SDK\_SSMS\_ONLY

CACHE\_POLICY: Based on this property flags it will be decided whether to keep a local cache copy of the property and whether to synchronize changes to it between SDK and SSMS. This flags has the 4 following possible values:

* CACHE\_POLICY\_NO\_CACHING
* CACHE\_POLICY\_SDK\_CACHE\_ONLY
* CACHE\_POLICY\_SYNCHRONIZE\_FROM\_SDK
* CACHE\_POLICY\_SYNCHRONIZE\_FROM\_SSMS

The following Flag/owner combinations not allowed for the App:

* CACHE\_POLICY is CACHE\_POLICY\_SDK\_CACHE\_ONLY and READ\_ONLY is set.
* CACHE\_POLICY is CACHE\_POLICY\_SYNCHRONIZE\_FROM\_SDK and READ\_ONLY} is set
* CACHE\_POLICY is CACHE\_POLICY\_SDK\_CACHE\_ONLY and property owner is OWNER\_USER or OWNER\_GROUP
* CACHE\_POLICY is CACHE\_POLICY\_SYNCHRONIZE\_FROM\_SSMS
* APP\_PORTAL\_ACCESS is APP\_PORTAL\_ACCESS\_NO\_APP or APP\_PORTAL\_ACCESS\_SDK\_SSMS\_ONLY
* IN\_KEYSTORAGE while keystorage is not opened

| Flag | Value | Description |
| --- | --- | --- |
| NONE | 0x00 | No flag is set. |
| VALUE\_ENCRYPTED | 0x02 | If set, a value to be saved in the database will be saved encrypted. |
| CONFIDENTIAL | 0x04 | Do never display this entry in the SSMS GUI. |
| UNIQUE\_TO\_USER | 0x08 | The value of this property must be unique to all devices belonging to same user. |
| READ\_ONLY | 0x20 | This property may not be written by portal and App. |
| APP\_PORTAL\_ACCESS\_ALL | 0x00000000 | App and portal may access the property. This is the default |
| APP\_PORTAL\_ACCESS\_NO\_PORTAL | 0x00000040 | The portal may not access the property. |
| APP\_PORTAL\_ACCESS\_NO\_APP | 0x00000080 | The App may not access the property. |
| APP\_PORTAL\_ACCESS\_SDK\_SSMS\_ONLY | 0x000000C0 | Neither App nor portal may access the Property. |
| CACHE\_POLICY\_NO\_CACHING | 0x00000000 | The SDK will not keep a local copy. The App will be informed about modifications to this property on the SSMS-side by call to onPropertySynchronization. |
| CACHE\_POLICY\_SDK\_CACHE\_ONLY | 0x100 | The SDK will keep a local-only copy. It will never synchronize it with the SSMS. |
| CACHE\_POLICY\_SYNCHRONIZE\_FROM\_SDK | 0x0200 | The SDK will keep a local copy and propagate modifications to the SSMS. If the property owner is OWNER\_DEVICE, it will never accept modifications from the SSMS. If the property owner is OWNER\_USER or OWNER\_GROUP, the SDK will accept modifications. That way a modification of a property belonging to a user with this caching policy will be propagated to all devices of this user. |
| CACHE\_POLICY\_SYNCHRONIZE\_FROM\_SSMS | 0x300 | The SDK will keep a local copy and modify in accordance to modifications on the SSMS automatically. The App will be informed after this was done. This value may not be used by the App while setting a property. |
| IN\_KEYSTORAGE | 0x00000400 | The SDK will allow access to this property only if the keystorage is opened. This flag may only be set, if the CACHE\_POLICY is not CACHE\_POLICY\_NO\_CACHING |
| SYNCHRONIZATION\_PENDING | 0x00000800 | With this flags the SDK informs the App that a cached property was modified, but this modification was not yet propagated to the SSMS. It may not be set during write accesses. It can only be set, if the CACHE\_POLICY is CACHE\_POLICY\_SYNCHRONIZE\_FROM\_SDK |
