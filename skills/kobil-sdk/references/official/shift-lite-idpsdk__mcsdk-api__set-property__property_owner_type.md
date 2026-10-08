> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/set-property/property_owner_type> on 2026-09-28. Converted to Markdown; wording unchanged.

# Property Owner Type

Property type is a parameter where you define what property type you want to set. Please take a look at the enum of available types.

| Type | Description |
| --- | --- |
| Device | This property will be available only from current device |
| User | This property will be available for current user |
| Group | This property will be available for current user's group |

Swift

```
/*! KSMPropertyOwnerType */
typedef NS_ENUM(NSInteger, KSMPropertyOwnerType) {
KSMDevice = 0,
KSMUser,
KSMGroup
};
```

Kotlin

```
public enum PropertyOwnerType {
DEVICE, USER, GROUP;
private PropertyOwnerType() { /* compiled code */ }
}
```

Flutter

```
static const PropertyOwnerType device = PropertyOwnerType._(0);
static const PropertyOwnerType user = PropertyOwnerType._(1);
static const PropertyOwnerType group = PropertyOwnerType._(2);
static const Map<int, PropertyOwnerType> values = {
0: device,
1: user,
2: group
};
```
