> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/digitanium-shift-migration> on 2026-09-28. Converted to Markdown; wording unchanged.

# Digitanium to Shift Migration Flow

## Digitanium to Shift Migration Flow

The migration flow allows existing Digitanium (SSMS) users to transition to a Shift (Maverick) backend. This is a multi-step process starting with a valid SSMS activation and login, obtaining a Shift activation code, switching environments, completing activation in Shift, and optionally obtaining authorization tokens for backend services.

### High-Level Flow Overview

#### Step 1: SSMS Login

* StartLoginEvent → LoginResultEvent

#### Step 2: Get Shift Activation Code

* Use SSMS login to obtain activation code for Shift

#### Step 3: Switch to Shift Environment

* Switch to Shift server assets, perform RestartEvent

#### Step 4: Shift Activation

* KSSIDP.activate(...) or SetAuthorisationCodeEvent → SetAuthorisationCodeResultEvent

#### Step 5: Exchange IAM Token (Optional)")

* ExchangeIamTokenEvent → ExchangeIamTokenResultEvent (retrieve token for authorizing special requests to backend services)

#### Step 5b: Get IAM Token Claims (Optional)")

* GetIamAccessTokenClaimsEvent → GetIamAccessTokenClaimsResultEvent (check claims and permissions of the IAM token)

#### Step 6: Delete SSMS User & Complete Migration

* Delete legacy SSMS user from system → Migration Complete

## Example Flow Migration For Existing SSMS Users

An existing user can be migrated like follows:

![](https://www.plantuml.com/plantuml/png/xLLDZzem4BtxLupe9KXDfHuNiMYXkvKeYxfQRzkpSIPW9TYfno7btrTE88t3n-wXwgaN56QUtyoyUKxko0dhoctEc93EM9ZMluBW6w5bXR1EILK8xM1Q53u-c1R584WiF_7xHPsgdy9aHgIIuWXOS3w_Vu8Jr4peJEdrJCWCTL93mr08NtoTpHyvoj8YHxj3sv3xAFY0aaW3nfYV0UA9Rtq4t4_g7zdQchA0T-d7c_GcXQNOhn38R17mboAdzFhO3tpEJSNyuF6ar-C8rkZWouyNU34PQd06X9H81Al3sTLX63eqn50dHwvQg17KuZ_iKBiwCOw3n3DIcNVInq7a1cK6AeKewkC-K99n9no28X3IgPrmokXd_5agYyaGZ8NShDMV21Ev0vLUeRgzFKSaT09HgvUVsSzlIks6THMLHYgzHXgsqV1LVhbUoIG1eOtRe8KBDNfBV3YxkNh_uxYHxT4N12ujeWwTuVzeiKLu4aILiScbbPy7ZkFNWNuVqbYBqdbrwlAAG6C5pdITqMUI5eN36kybujvHVCbPY8id9rSYE9eUQlgUtdvqskuz90XaxO0QRQ5IRdD6WGvmWVk8B_cmPUhT_n7GOSw6B3nwbAfzjNIRYDvKUCWm9tpb3bqnVdT_9Q7zovxtj3sxNxGo_3VElpNEvRlADwQ2fMXN4xMVX_VWhD3a_MGqp7LgQDYJynpXTxGgtJSKbrur_QAXo2VPEzH9kSr_0m00)

## Example Login Flow With Transaction

![](https://www.plantuml.com/plantuml/png/fLJ1Rk903BtFLrYSG28_WBgeOTi3Ir5N2hizMnEJZWAUaMS2sxzVJG8D8UcMQYyeylDxjfyztFk04ghzJYdKmGgazIzw-EL9b4C9HXk7721rBiP7gNEZ3h3-dZsiQgZ-weAbzoPtvuHLbYqVVa8lQu5S6YuMg4lYl4xjXhhfg-V5yYaZNGbb90UIHZn68GQC9ZzIIXLYAmTFjZ2iLEm_cRSDpHfW70TbtDCK77f_j99FLDjrCkzN-nSpLhbBBgiyhzvhr_xCuF6FVaKkQ9ckDxOaFfDEy8-N3RJnP7xbpWooLtk4DHg6J0iHZzyPKmY2x547OncMlBL-egxC7H3yJMAsRz1fvhEYAauV4rFd1b3Y_6J_sZAzmQRjgs4cyuRPWyS38tnWH9_xlquSQYTQcI7Em3tStaB_TDkxkC64zaesOeg2P87C98y7ud1rPLbysJtRkxTPh-qY1ruCv_ReXygVjtP1rvQtHlOUh816rhJpNvBiFBDJsrihHvJSZq_Ytu9KD0Ll2gPyG6IYcl-VuSLyNUscVQCletHdJY5VxS8r_oxvv5xElFXWxedpQh_x2m00)
