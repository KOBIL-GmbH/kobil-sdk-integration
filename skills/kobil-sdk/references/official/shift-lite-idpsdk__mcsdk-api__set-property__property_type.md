> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/set-property/property_type> on 2026-09-28. Converted to Markdown; wording unchanged.

# Property Type

Property type is a parameter where you define what property type you want to set. Please take a look at the enum of available types.

Swift

```
/*! KSMPropertyType */
typedef NS_ENUM(NSInteger, KSMPropertyType) {
KSMInvalid = -1,
KSMOctetString = 0,
KSMUtf8String,
};
```

Kotlin

```
public enum PropertyType {
INVALID, OCTET_STRING, UTF8_STRING
}
```

Flutter

```
static const PropertyType invalid = PropertyType._(-1);
static const PropertyType octetString = PropertyType._(0);
static const PropertyType utf8String = PropertyType._(3);
static const Map<int, PropertyType> values = {
-1: invalid,
0: octetString,
3: utf8String,
};
```
