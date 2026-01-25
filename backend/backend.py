from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import time
import threading
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)
CORS(app)

# JSON file to store emails
EMAILS_FILE = 'emails.json'

# Global state for scan simulation
scan_state = {
    'status': 'IDLE',  # IDLE, RUNNING, NEEDS_APPROVAL, COMPLETED, TERMINATED
    'logs': [],
    'pending_action': None,
    'thread': None,
    'targets': [],
    'scan_type': '',
    'action_denied': False,
    'report_type': 'sql_injection'  # 'sql_injection' or 'sensitive_data'
}

def load_emails():
   # loads emails from the json file 
    if os.path.exists(EMAILS_FILE):
        try:
            with open(EMAILS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_emails(emails_dict):
    # saves emails to the json file
    with open(EMAILS_FILE, 'w') as f:
        json.dump(emails_dict, f, indent=2)

@app.route('/verify', methods=['POST'])
def verify_email():
    """
    API endpoint to "verify" an email.
    Returns both the email and username extracted from the email.
    Saves the email to emails.json file.
    """
    # "verifies" the email - for now, it just accepts the email as verified and adds it to database. 
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
        
        # ensures duplicate emails are not added
        email_exists = any(e.get('email') == email for e in emails_dict['emails'])
        
        if not email_exists:
            emails_dict['emails'].append({
                'email': email,
                'username': username,
                'timestamp': datetime.now().isoformat()
            })
            
            # save to file
            save_emails(emails_dict)
        
        return jsonify({
            "success": True, 
            "username": username,
            "email": email  
        })
    except Exception as e:
        # Handle any unexpected errors
        return jsonify({"success": False, "message": str(e)}), 500


def run_scan_simulation():
    """
    Multi-stage HITL workflow simulation.
    Phase 1: SQL Injection discovery -> Ask for approval
    Phase 2 (if denied): Pivot to backup file discovery -> Ask for approval again
    """
    global scan_state
    
    # ===== PHASE 1: SQL Injection Discovery =====
    initial_logs = [
        f"[INFO] Starting reconnaissance on targets: {', '.join(scan_state['targets'])}",
        "[SCAN] Initializing Nmap port scanner...",
        "[SCAN] Discovered Port 80 (HTTP) - OPEN",
        "[SCAN] Discovered Port 443 (HTTPS) - OPEN",
        "[AI] Querying RAG database for known vulnerabilities...",
        "[ALERT] Identified potential SQL Injection vulnerability on login form"
    ]
    
    for log in initial_logs:
        # Check for emergency termination or other stops
        if scan_state['status'] not in ['RUNNING', 'NEEDS_APPROVAL']:
            return
        scan_state['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': log
        })
        time.sleep(1.5)
    
    # FIRST APPROVAL POINT: SQL Injection
    scan_state['status'] = 'NEEDS_APPROVAL'
    scan_state['pending_action'] = 'Execute SQLMap dump on target DB'
    
    while scan_state['status'] == 'NEEDS_APPROVAL':
        time.sleep(0.5)
    
    # Check if first action was APPROVED
    if not scan_state.get('action_denied', False):
        # APPROVED PATH: Execute SQL attack
        if scan_state['status'] != 'RUNNING':
            return
            
        sql_attack_logs = [
            "[ACTION] Executing SQLMap on detected vulnerability...",
            "[PROGRESS] SQLMap running... analyzing injection points",
            "[SUCCESS] Database structure extracted successfully",
            "[DATA] Retrieved 1,247 user records",
            "[REPORT] Generating comprehensive security report...",
            "[COMPLETE] Scan finished. Report saved to /reports/scan_result.pdf"
        ]
        
        for log in sql_attack_logs:
            if scan_state['status'] != 'RUNNING':
                return
            scan_state['logs'].append({
                'timestamp': datetime.now().isoformat(),
                'message': log
            })
            time.sleep(1.5)
        
        # Set report type and complete
        scan_state['report_type'] = 'sql_injection'
        scan_state['status'] = 'COMPLETED'
        return
    
    # ===== PHASE 2: Backup File Discovery (Denial Path) =====
    scan_state['action_denied'] = False  # Clear flag
    
    # Pivot to safer strategy
    pivot_logs = [
        "[USER] Action denied by operator",
        "[AI] Acknowledged. Skipping destructive SQL payload",
        "[AI] Pivoting strategy to passive file enumeration...",
        "[SCAN] Checking for sensitive backup files...",
        "[ALERT] Found exposed backup: database.bak"
    ]
    
    for log in pivot_logs:
        if scan_state['status'] != 'RUNNING':
            return
        scan_state['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': log
        })
        time.sleep(1.5)
    
    # SECOND APPROVAL POINT: Backup File Download
    scan_state['status'] = 'NEEDS_APPROVAL'
    scan_state['pending_action'] = 'Download exposed backup file (database.bak)'
    
    while scan_state['status'] == 'NEEDS_APPROVAL':
        time.sleep(0.5)
    
    # Check if second action was APPROVED
    if not scan_state.get('action_denied', False):
        # APPROVED PATH: Download backup
        if scan_state['status'] != 'RUNNING':
            return
            
        backup_download_logs = [
            "[ACTION] Downloading backup file...",
            "[PROGRESS] Transfer in progress... 2.4 MB",
            "[SUCCESS] Backup file downloaded successfully",
            "[DATA] Found 847 user credentials in backup",
            "[REPORT] Generating security report...",
            "[COMPLETE] Scan finished. Report saved to /reports/scan_result.pdf"
        ]
        
        for log in backup_download_logs:
            if scan_state['status'] != 'RUNNING':
                return
            scan_state['logs'].append({
                'timestamp': datetime.now().isoformat(),
                'message': log
            })
            time.sleep(1.5)
        
        # Set report type and complete
        scan_state['report_type'] = 'sensitive_data'
        scan_state['status'] = 'COMPLETED'
        return
    
    # DENIED TWICE: Just complete with what we have
    scan_state['action_denied'] = False
    final_log = {
        'timestamp': datetime.now().isoformat(),
        'message': "[USER] Second action denied. Scan terminated by operator"
    }
    scan_state['logs'].append(final_log)
    scan_state['report_type'] = 'sensitive_data'  # Partial findings
    scan_state['status'] = 'COMPLETED'


@app.route('/start_scan', methods=['POST'])
def start_scan():
    """
    Endpoint to start the AI agent scan simulation.
    Accepts targets and scan_type from the frontend.
    """
    global scan_state
    
    # Check if a scan is already running
    if scan_state['status'] == 'RUNNING':
        return jsonify({
            "success": False,
            "message": "A scan is already in progress"
        }), 400
    
    data = request.json
    targets = data.get('targets', [])
    scan_type = data.get('scan_type', 'web')
    
    if not targets:
        return jsonify({
            "success": False,
            "message": "No targets provided"
        }), 400
    
    # Reset and initialize scan state
    scan_state['status'] = 'RUNNING'
    scan_state['logs'] = []
    scan_state['pending_action'] = None
    scan_state['targets'] = targets
    scan_state['scan_type'] = scan_type
    
    # Start background thread
    thread = threading.Thread(target=run_scan_simulation, daemon=True)
    thread.start()
    scan_state['thread'] = thread
    
    return jsonify({
        "success": True,
        "message": "Scan started successfully"
    })


@app.route('/poll_status', methods=['GET'])
def poll_status():
    """
    Endpoint for frontend to poll the current scan status.
    Returns logs, current status, and report type.
    """
    return jsonify({
        "status": scan_state['status'],
        "logs": scan_state['logs'],
        "pending_action": scan_state['pending_action'],
        "targets": scan_state['targets'],
        "scan_type": scan_state['scan_type'],
        "report_type": scan_state['report_type']
    })


@app.route('/approve_action', methods=['POST'])
def approve_action():
    """
    Endpoint to approve the pending action and resume the scan.
    """
    global scan_state
    
    if scan_state['status'] != 'NEEDS_APPROVAL':
        return jsonify({
            "success": False,
            "message": "No action pending approval"
        }), 400
    
    # Resume the scan (aggressive path)
    scan_state['status'] = 'RUNNING'
    scan_state['pending_action'] = None
    scan_state['action_denied'] = False
    
    return jsonify({
        "success": True,
        "message": "Action approved, resuming scan"
    })


@app.route('/deny_action', methods=['POST'])
def deny_action():
    """
    Endpoint to deny the pending action and pivot to safer strategy.
    """
    global scan_state
    
    if scan_state['status'] != 'NEEDS_APPROVAL':
        return jsonify({
            "success": False,
            "message": "No action pending approval"
        }), 400
    
    # Resume scan but with denial flag (will trigger pivot logic)
    scan_state['status'] = 'RUNNING'
    scan_state['pending_action'] = None
    scan_state['action_denied'] = True
    
    return jsonify({
        "success": True,
        "message": "Action denied, AI pivoting to safer strategy"
    })


@app.route('/kill_scan', methods=['POST'])
def kill_scan():
    """
    EMERGENCY KILL SWITCH: Immediately terminate the running scan.
    """
    global scan_state
    
    if scan_state['status'] not in ['RUNNING', 'NEEDS_APPROVAL']:
        return jsonify({
            "success": False,
            "message": "No active scan to terminate"
        }), 400
    
    # Immediately terminate the scan
    scan_state['status'] = 'TERMINATED'
    scan_state['pending_action'] = None
    
    # Add emergency termination log
    scan_state['logs'].append({
        'timestamp': datetime.now().isoformat(),
        'message': '[EMERGENCY] KILL SWITCH ACTIVATED. TERMINATING ALL PROCESSES IMMEDIATELY'
    })
    
    return jsonify({
        "success": True,
        "message": "Scan terminated by emergency kill switch"
    })


@app.route('/reset_scan', methods=['POST'])
def reset_scan():
    """
    Endpoint to reset the scan state (useful for testing).
    """
    global scan_state
    
    scan_state['status'] = 'IDLE'
    scan_state['logs'] = []
    scan_state['pending_action'] = None
    scan_state['targets'] = []
    scan_state['scan_type'] = ''
    scan_state['action_denied'] = False
    scan_state['report_type'] = 'sql_injection'
    
    return jsonify({
        "success": True,
        "message": "Scan state reset"
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)

