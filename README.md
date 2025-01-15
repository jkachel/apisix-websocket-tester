# WebSockets: Authentication via APISIX

APISIX supports routing WebSocket traffic, and can be used to provide an authentication layer for these requests. To test and demonstrate this, I set up a simple test rig application, consisting of a very simple HTML frontend and a Python backend that uses the WebSockets package directly. The test rig is available [here](https://github.com/jkachel/apisix-websocket-tester).

## Testing setup

The test rig consists of 3 parts:

- The WebSockets server. This is a simple echo server - it has a bit of extra code to parrot back the user's username back at them when they connect, but otherwise it just echos things.
- A HTML/JS frontend. This is a single file served by nginx that establishes a WebSocket connection to the server and provides a pretty minimal interface for composing and displaying the messages sent. (This is served by nginx.)
- The authentication layer, using APISIX as the API gateway and Keycloak as the SSO source. For expediency, this pulls _most_ of the config from Unified Ecommere but there are some changes to the APISIX routes for obvious reasons.

A production app would not be written directly with WebSockets necessarily, but the same techniques the test rig uses to retrieve user data can be used in a more feature-complete application.

## Authentication Flow

As noted, APISIX supports WebSockets as one of the protocols that it can manage, and this includes configuring plugins for various purposes (such as authentication). APISIX will attempt to authenticate the user depending on what plugins are configured. For OL apps, this means using OIDC to Keycloak (via the `openid-connect` plugin), but this could also be via other methods.

WebSocket connections are established first via a handshake, which is done over HTTP. APISIX will use this step to determine what the user's authentication status is, and will take an action depending on that status and the route's configuration:

* If the user is authenticated, APISIX will pass the request along to the service. APISIX will also attach user data to the incoming request: an `X-Userinfo` header that contains the user's account details in a base64-encoded JSON payload is added to the handshake request that is sent to the WebSocket server. The WebSocket server can parse the headers that are sent during the handshake and perform whatever processes it needs to act on behalf of the named user for the session.
* If the user doesn't have a session, then the route's configuration determines what APISIX does next. APISIX can simply deny the request and return a `401 Unauthorized` response, it can pass the request along without any user data, or it can attempt to establish a new session for the user.

### Establishing a Session

If APISIX attempts to establish a new session for the user, it will do so by trying to redirect them through the identity provider. For normal HTTP requests, the user would get a login screen, authenticate with the identity provider, and then be sent back to APISIX; APISIX would then internally set up a session for the user and maintain it.

However, WebSockets don't generally handle return codes other than `101 Switching Protocols` from the handshake process. So, if the user is redirected, the WebSocket connection will fail. (It will also obviously fail if APISIX is set to deny the request.) So, a session needs to exist in APISIX _first_ if the WebSocket service needs to know about the user. 

There's a few avenues for doing this:

- If the user has an existing session, APISIX will reuse it. So, if the frontend (or some other part of the app, like the REST API) is routed through APISIX, it should pick up the session from there. This is essentially the route the test rig uses. You need to log in to accesss the frontend via APISIX, so the WebSocket connection simply reuses that session. 
- APISIX can simply pass the connection along without user data. In this case, the app will need to either be accessible in some form by anonymous users, or it will need to have a protocol that tells the frontend that a session needs to be established.

Apps should avoid treating errors on connect as authentication errors. [By design](https://websockets.spec.whatwg.org/#eventdef-websocket-error), WebSockets errors don't contain any real data in them.

### Getting User Data

The data that gets passed via APISIX into the user info header is dependent on what scopes are set up and how the realm and client are set up. You can usually expect at least an email address and the ID that Keycloak has for the user, though. The app can use whatever method it needs to map this to a user - for example, Unified Ecommerce uses the Keycloak ID as the identifier and creates or updates a Django user based on it.

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
