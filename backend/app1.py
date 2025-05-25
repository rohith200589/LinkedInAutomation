from flask import Flask, redirect, request, session, jsonify, url_for
from requests_oauthlib import OAuth2Session
import requests
import os
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_for_dev")

# Enable CORS for frontend communication
CORS(app, supports_credentials=True)

# LinkedIn OAuth Configuration
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5050/callback")

AUTHORIZATION_BASE_URL = "https://www.linkedin.com/oauth/v2/authorization "
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken "
POST_URL = "https://api.linkedin.com/v2/ugcPosts "

@app.route("/")
def home():
    return jsonify({"status": "Running"})


@app.route("/linkedin/login")
def linkedin_login():
    linkedin = OAuth2Session(
        LINKEDIN_CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=["w_member_social"]
    )
    authorization_url, state = linkedin.authorization_url(AUTHORIZATION_BASE_URL)
    session["oauth_state"] = state
    return redirect(authorization_url)


@app.route("/linkedin/callback")
def linkedin_callback():
    linkedin = OAuth2Session(
        LINKEDIN_CLIENT_ID,
        state=session["oauth_state"],
        redirect_uri=REDIRECT_URI
    )
    token = linkedin.fetch_token(
        TOKEN_URL,
        client_secret=LINKEDIN_CLIENT_SECRET,
        authorization_response=request.url
    )
    session["linkedin_token"] = token
    return redirect("http://localhost:5173")  # Redirect back to frontend


@app.route("/linkedin/post", methods=["POST"])
def linkedin_post():
    token = session.get("linkedin_token")
    if not token:
        return jsonify({"error": "Not authenticated"}), 401

    content = request.json.get("content")
    if not content:
        return jsonify({"error": "No content provided"}), 400

    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    try:
        # Get user info
        person_response = requests.get("https://api.linkedin.com/v2/userinfo ", headers=headers)
        person_data = person_response.json()
        author_urn = f"urn:li:person:{person_data['sub']}"

        # Build post data
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        response = requests.post(POST_URL, headers=headers, json=post_data)

        return jsonify({
            "success": True,
            "status_code": response.status_code,
            "response": response.json()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5050)
