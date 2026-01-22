from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)
# Enable CORS (Cross-Origin Resource Sharing)
CORS(app)

# JSON file to store emails
EMAILS_FILE = 'emails.json'

def load_emails():
    """Load emails from JSON file. Returns empty dict if file doesn't exist."""
    if os.path.exists(EMAILS_FILE):
        try:
            with open(EMAILS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_emails(emails_dict):
    """Save emails dictionary to JSON file."""
    with open(EMAILS_FILE, 'w') as f:
        json.dump(emails_dict, f, indent=2)

@app.route('/verify', methods=['POST'])
def verify_email():
    """
    API endpoint to "verify" an email.
    Returns both the email and username extracted from the email.
    Saves the email to emails.json file.
    """
    data = request.json
    #get email, null if not found pretty much
    email = data.get('email', '')

    if not email:
        #error if not
        return jsonify({"success": False, "message": "Email is required."}), 400

    
    # right now, email is just split to get username. when scale is expanded we will obviously be checking database....

    try:
        username = email.split('@')[0]
        
        # Load existing emails
        emails_dict = load_emails()
        
        # Add new email with timestamp
        if 'emails' not in emails_dict:
            emails_dict['emails'] = []
        
        # Check if email already exists (optional - you can remove this check if you want duplicates)
        email_exists = any(e.get('email') == email for e in emails_dict['emails'])
        
        if not email_exists:
            emails_dict['emails'].append({
                'email': email,
                'username': username,
                'timestamp': datetime.now().isoformat()
            })
            
            # Save back to file
            save_emails(emails_dict)
        
        return jsonify({
            "success": True, 
            "username": username,
            "email": email  
        })
    except Exception as e:
        # Handle any unexpected errors
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == '__main__':

    app.run(debug=True, port=5000)

