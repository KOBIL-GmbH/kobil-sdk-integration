> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/enrollment/test_user_registration_activation_login_digitanium+_shift> on 2026-09-28. Converted to Markdown; wording unchanged.

# Details

### User registration

User accounts are created by KOBIL IDP, depending on its configuration they are requested by:

* user in a self enrollment process with the app
* administrator in the KOBIL IDP Admin Web UI

In both cases a password is defined for the user.

> **Note**: For additional details see KOBIL IDP documentation.

### User account activation

The user account activation is part of the self enrollment process with the app.
You do not need an activation code for this, depending on KOBIL IDP's configuration you have to enter your password defined in user registration.

### User account login

The user account login is done inside the app, token from KOBIL IDP are used for it. The Login is part of different flows:

* first login as part of self enrollment process
* subsequent login with valid IDP token - user can directly use the app
* subsequent login with invalid IDP token - user has to enter his password to get new IDP token before using the app
