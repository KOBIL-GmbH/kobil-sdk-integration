# Profile photo (iOS)

The user chooses or takes a profile photo, cropped to a circle and shown
in the profile and home avatars. Check the backend first: whether the photo can be uploaded
depends on a service that most MCSDK environments do not have.

## 1. Is the profile service deployed?

The upload goes through a separate KOBIL **profile service**, not AST:

- Token: `KSMExchangeIamTokenEvent` with audience `userPortalPublic`.
- Upload: `KSMCreateHttpCommonRequestEvent`, POST
  `https://profile.<env host>/api/v1/profile-picture/`, header `Authorization: ******`
  (the MasterController inserts the exchanged token), JSON body `{"image": "<base64 JPEG>"}`.
- The IDP's `picture` claim then holds the picture id; GET `<url><id>` returns
  `{"image": "<base64>"}`.

Before writing any upload code, prove the host exists (read-only):

```sh
curl -s -o /dev/null -w '%{http_code}\n' https://profile.<env host>/api/v1/profile-picture/
kubectl --context <cluster> get virtualservices -A | grep -i profile
```

An `istio-envoy` 404 on every path and no `profile.` host in the VirtualServices means it is
not deployed (the case on the development environment tested, 2026-09-26). Then store the photo locally as
below and tell the customer that a synced photo needs the backend team to deploy the profile
service. Do not invent another endpoint, and do not put the photo in the SDK user data store
(it is meant for small values such as the signature JSON).

## 2. Local photo (copy these files)

| File | Role |
|---|---|
| `ios/profile/ProfilePhotoStore.swift` | `@Observable`; one JPEG per user in Application Support, file name = SHA-256 of the user id, complete file protection, stored square (512 px). `load(for:)`, `save(_:)`, `delete()`, `reset()`; `save` throws `notSignedIn` before `load` |
| `ios/profile/ProfilePhotoPicker.swift` | `.profilePhotoPicker(isPresented:store:)`: confirmation dialog (Choose Photo, Take Photo, Remove Photo), `PhotosPicker`, a `UIImagePickerController` camera, and `PhotoCropView` (pan and pinch inside a circle, Choose/Cancel) |
| `ios/ui/Theme.swift` | `AvatarView(name:size:image:)` shows the photo or the initials |

Wiring:

```swift
@State private var profilePhoto = ProfilePhotoStore()          // App; .environment(profilePhoto)

.task(id: session.phase == .loggedIn) {                         // root view
    if session.phase == .loggedIn,
       let userID = session.sdkInformation?.loggedInUserId ?? session.currentUserIdentifier {
        profilePhoto.load(for: userID)
    } else {
        profilePhoto.reset()
    }
}

Button { editsPhoto = true } label: {                           // profile header
    AvatarView(name: session.userDisplayName, size: 84, image: profilePhoto.image)
}
.profilePhotoPicker(isPresented: $editsPhoto, store: profilePhoto)
```

Use the same `AvatarView(…, image: profilePhoto.image)` on Home so both update together.

Info.plist: `NSCameraUsageDescription` (build setting
`INFOPLIST_KEY_NSCameraUsageDescription`) is required for Take Photo; without it the app
crashes when the camera opens. `PhotosPicker` needs no photo-library permission. The camera
option is hidden when `UIImagePickerController.isSourceTypeAvailable(.camera)` is false (the
simulator), so test Take Photo on a device.

## Verify

- Unit tests `ProfilePhotoTests` in `ios/tests/SigningAndPhotoTests.swift`: per-user files,
  square output, `save` refused without a user.
- On the device: Profile → tap the avatar → Choose Photo / Take Photo → move and zoom →
  Choose. The photo shows on Profile and Home, survives a relaunch, disappears on logout and
  returns on the next login of the same user.
