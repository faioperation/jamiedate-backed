import requests
from django.conf import settings
from decouple import config


def get_access_token(user):
    """
    Returns the appropriate access token based on the user's platform.
    """
    # Use IG_PAGE_ACCESS_TOKEN for Instagram users if available
    ig_token = getattr(settings, "IG_PAGE_ACCESS_TOKEN", None)
    if user.platform == "instagram" and ig_token:
        return ig_token
    return settings.FB_PAGE_ACCESS_TOKEN


def send_fb_message(user, text):
    """
    Sends a message to the user via Facebook, Instagram, or WhatsApp.
    """
    recipient_id = user.sender_id
    token = get_access_token(user)

    if user.platform == "whatsapp":
        # WhatsApp Cloud API
        phone_number_id = config("WHATSAPP_PHONE_NUMBER_ID", default="")
        if not phone_number_id:
            print("WHATSAPP_PHONE_NUMBER_ID not configured")
            return False, "WHATSAPP_PHONE_NUMBER_ID missing"

        url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {"body": text},
        }
    elif user.platform == "instagram" and token and token.startswith("IGA"):
        version = (
            settings.FB_API_URL.split("/")[-1]
            if "v" in settings.FB_API_URL
            else "v21.0"
        )
        url = f"https://graph.instagram.com/{version}/me/messages"
        payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    else:
        url = f"{settings.FB_API_URL}/me/messages"
        payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        res = requests.post(url, headers=headers, json=payload)
        print(f"{user.platform.upper()} Send Status: {res.status_code}")
        if res.status_code == 200 or res.status_code == 201:
            try:
                data = res.json()
                msg_id = data.get("message_id") or data.get("messages", [{}])[0].get(
                    "id"
                )
            except Exception:
                msg_id = None
            return True, msg_id
        else:
            error_msg = res.text
            print(f"{user.platform.upper()} Send Error: {error_msg}")
            return False, error_msg
    except Exception as e:
        error_msg = str(e)
        print(f"Error sending {user.platform} message: {error_msg}")
        return False, error_msg


def fetch_user_info(user):
    """
    Fetches user profile information from Meta Graph API.
    """
    token = get_access_token(user)

    if user.platform == "instagram" and token and token.startswith("IGA"):
        version = (
            settings.FB_API_URL.split("/")[-1]
            if "v" in settings.FB_API_URL
            else "v21.0"
        )
        url = f"https://graph.instagram.com/{version}/{user.sender_id}"
        params = {
            "fields": "name,username,profile_pic",
            "access_token": token,
        }
    else:
        url = f"{settings.FB_API_URL}/{user.sender_id}"
        params = {
            "fields": "first_name,last_name,name,username,profile_pic",
            "access_token": token,
        }

    print(f"--- Fetching Info for: {user.sender_id} ---")

    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Graph API Status (Combined): {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            update_user_data(user, data)
            return

        # If combined fails, try only first_name and last_name
        print("Combined fetch failed, trying first_name and last_name only...")
        params["fields"] = "first_name,last_name"
        response = requests.get(url, params=params, timeout=10)
        print(f"Graph API Status (Granular): {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            update_user_data(user, data)
            return

        # Still failing, log detailed error
        print(f"Failed to fetch user info. Status: {response.status_code}")
        try:
            err_data = response.json().get("error", {})
            print(f"FB Error: {err_data.get('message')} (Code: {err_data.get('code')})")
        except Exception:
            print(f"Raw Error Body: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Network error fetching user info: {e}")


def update_user_data(user, data):
    """
    Updates the user model instance with fetched Meta profile data.
    """
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    full_name = data.get("name")
    username = data.get("username")

    if full_name:
        user.name = full_name
    elif first_name or last_name:
        user.name = f"{first_name or ''} {last_name or ''}".strip()
    elif username:
        user.name = username

    # Accommodate both FB and IG profile picture fields
    if "profile_pic" in data:
        user.profile_pic = data.get("profile_pic")
    elif "profile_picture_url" in data:
        user.profile_pic = data.get("profile_picture_url")

    user.save()
    print(f"User info updated: {user.name}")
