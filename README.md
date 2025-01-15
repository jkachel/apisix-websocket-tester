# WebSockets: Authentication via APISIX

APISIX supports routing WebSocket traffic, and can be used to provide an authentication layer for these requests. To test and demonstrate this, I set up a simple test rig application, consisting of a very simple HTML frontend and a Python backend that uses the WebSockets package directly.

## Testing setup

The test rig consists of 3 parts:

- The WebSockets server. This is a simple echo server - it has a bit of extra code to parrot back the user's username back at them when they connect, but otherwise it just echos things.
- A HTML/JS frontend. This is a single file served by nginx that establishes a WebSocket connection to the server and provides a pretty minimal interface for composing and displaying the messages sent. (This is served by nginx.)
- The authentication layer, using APISIX as the API gateway and Keycloak as the SSO source. For expediency, this pulls _most_ of the config from Unified Ecommere but there are some changes to the APISIX routes for obvious reasons.

A production app would not be written directly with WebSockets necessarily, but the same techniques the test rig uses to retrieve user data can be used in a more feature-complete application.

## Authentication Flow

As noted, APISIX supports WebSockets as one of the protocols that it can manage, and this includes configuring plugins for various purposes (such as authentication). The test rig is set up with two routes in APISIX. One route (for `/`) is for delivering the frontend. The second proxies the WebSocket connection to the echo server. Both of these are set up with the `openid-connect` plugin to authenticate the user via Keycloak.

WebSocket connections are established first via a handshake, which is done over HTTP. This gives APISIX an opportunity to attach user data to the incoming request. If the user is authenticated (i.e., has a session that's managed by APISIX), it will attach a `X-Userinfo` header that contains the user's account details in a base64-encoded JSON payload. The WebSocket server can parse the headers that are sent during the handshake and perform whatever processes it needs to act on behalf of the named user.

One of the pain points is establishing a session - you can set up APISIX to use OIDC on the WebSocket route, but handing unauthenticated users requires some additional work.

### Establishing a Session

WebSockets don't generally handle return codes other than `101 Switching Protocols` from the handshake process well. If the user does not have a session set up, APISIX may try to redirect the user through Keycloak when they attempt to connect to the WebSocket server. This will fail. Or, it can be set up to deny the request, which will (obviously) fail.

So, a session needs to exist in APISIX _first_ if the WebSocket service needs to know about the user. There's a few avenues for doing this:

- If the user already has a session, then APISIX will reuse it.
- If the user doesn't have a session, the route to the WebSocket server can be set up to pass the connection along without authentication, rather than attempt to redirect them. (See notes below for testing this with the test rig.) The WebSocket server code then must implement a protocol to alert the frontend that there's no session, or otherwise enter some sort of limited access mode.
- If the user doesn't have a session, and the route in APISIX is set up to redirect, the frontend may want to interpret the resulting error as a `403`. The frontend should then have a path to authenticate the user.

> [!IMPORTANT]
> The last option is probably the worst choice, because this overloads the error event. [By design](https://websockets.spec.whatwg.org/#eventdef-websocket-error), the WebSockets JavaScript API exposes _no_ information about what the error _was_ - merely that an error occurred - so an error may not necessarily be because the user is anonymous.

#### Passing Anonymous Connections

The [relevant setting for the `openid-connect` plugin](https://apisix.apache.org/docs/apisix/plugins/openid-connect/) is `unauth_action`, which can be `deny`, `pass`, or `auth`. The default is `auth`, which will redirect the user through the identity provider. Setting this to `pass` will pass the connection on without any user data. 

The test rig server will identify the user as "anonymous". Otherwise, it assumes you're whatever `preferred_username` that Keycloak sends on (which is typically the email address).

### Getting User Data

The data that gets passed via APISIX into the user info header is dependent on what scopes are set up and how the realm and client are set up. You can usually expect at least an email address and the ID that Keycloak has for the user. The app can use whatever method it needs to map this to a user - for example, Unified Ecommerce uses the Keycloak ID as the identifier and creates or updates a Django user based on it.

## Using the Test Rig

A Docker Compose environment is included to bring the entire thing up.

Set up your `.env` file using the example provided, then run `docker compose build` to build the WebSocket server. Once that's done, `docker compose up` will bring the entire thing up. Once the app is running, you have access to these services:

| Service | Port | URL |
|---|---|---|
| Authenticated Front End | 6701 | http://localhost:6701 | 
| WebSocket Service | 6701 | ws://localhost:6701/ws |
| Keycloak Admin (HTTP) | 6702 | http://localhost:6702 |
| Keycloak Admin (HTTPS) | 6703 | http://localhost:6703 |
| Direct Unauthenticated Front End | 6705 | http://localhost:6705 | 
| Direct WebSocket Service | 6700 | ws://localhost:6700 |

The Authenticated Front End and WebSocket Service are routed through APISIX. The remainder are not.

The frontend app is set up to connect via APISIX. By default, the APISIX config is set to `pass` unauthenticated requests to the WebSocket service - you can change this in `config/apisix/config.yaml`. 

The Keycloak environment includes a handful of users that are created by default:

| User | Password |
|---|---|
| `student@odl.local` | `student` |
| `prof@odl.local` | `prof` |
| `admin@odl.local` | `admin` |

Note that these users don't have any sort of permissions - the app doesn't do anything that requires authentication.

Go to http://localhost:6701 or 6705 to test the app. This is a pretty simple interface. Going to the authenticated port will run you through Keycloak. 
