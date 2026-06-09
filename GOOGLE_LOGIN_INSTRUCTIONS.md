# Setting Up Real Google OAuth 2.0 Integration

The current Google Login flow in `MarketMind` is a simulated UI mock for demonstration purposes. To integrate actual Google OAuth 2.0 for production, follow these exact steps:

## Step 1: Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `marketmind-auth`).
3. In the sidebar, navigate to **APIs & Services > OAuth consent screen**.
4. Select "External" (or Internal if you are on Google Workspace) and fill out the required App Information (App name: MarketMind, support email, etc.).
5. Add scopes for `.../auth/userinfo.email` and `.../auth/userinfo.profile`.
6. Save and Continue.

## Step 2: Create Credentials
1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Application Type: **Web application**.
4. Name: MarketMind Web Client.
5. Authorized JavaScript origins:
   - `http://localhost:5173` (for local development)
   - `https://your-production-domain.com` (for production)
6. Authorized redirect URIs:
   - `http://localhost:5000/api/auth/google/callback` (for local development)
   - `https://api.your-production-domain.com/api/auth/google/callback` (for production)
7. Click **Create**. You will receive a `Client ID` and `Client Secret`.

## Step 3: Update Backend Variables
In your project root, add these to your `.env` file:
```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_DISCOVERY_URL=https://accounts.google.com/.well-known/openid-configuration
```

## Step 4: Implement Backend OAuth Flow (Flask)
You will need to install `requests` and `oauthlib`:
```bash
pip install requests oauthlib requests-oauthlib
```

Update `app.py` to use real OAuth. Replace the dummy `/api/auth/google` route:

```python
from oauthlib.oauth2 import WebApplicationClient
import requests

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
client = WebApplicationClient(GOOGLE_CLIENT_ID)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/api/auth/google")
def auth_google():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/api/auth/google/callback")
def auth_google_callback():
    code = request.args.get("code")
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET))

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.prepare_api_request(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create or update user in your USERS_DB (or SQLite)
    # Login the user by setting the session variable
    session["user_email"] = users_email

    # Redirect to the frontend React app
    return redirect("http://localhost:5173/")
```

Follow these instructions when you are ready to configure the live OAuth flow!
