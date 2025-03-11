import json
import os
import requests
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from bs4 import BeautifulSoup

app = Flask(__name__)

CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from the config file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"services": []}

def save_config(config):
    """Save configuration to the config file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def process_html_content(html_content):
    """Process HTML content to ensure proper rendering in cards.
    
    This function handles parsing and preprocessing of HTML content
    to ensure scripts and styles are properly isolated.
    """
    try:
        # Try using BeautifulSoup to parse and clean the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process script tags to ensure they execute properly in iframe
        for script in soup.find_all('script'):
            # Add defer attribute to external scripts to ensure they load properly
            if script.get('src'):
                script['defer'] = 'defer'
            
            # Remove any document.write calls which can break iframe rendering
            if script.string:
                script.string = script.string.replace('document.write', '// document.write')
        
        return str(soup)
    except Exception as e:
        # If parsing fails, return original content
        print(f"Error processing HTML content: {e}")
        return html_content

def fetch_data_from_service(service):
    """Fetch data from an external service."""
    try:
        response = requests.get(service['url'], timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            
            # Determine the data format based on content type
            if 'application/json' in content_type:
                data = response.json()
            elif 'text/html' in content_type:
                data = response.text
                # Process HTML content
                data = process_html_content(data)
                # Add our card container CSS to HTML content
                data = inject_card_container_css(data, service['name'])
            else:
                data = response.text
                
            return {
                'name': service['name'],
                'url': service['url'],
                'status': 'Connected',
                'data': data
            }
        else:
            return {
                'name': service['name'],
                'url': service['url'],
                'status': f'Error: HTTP {response.status_code}',
                'data': None
            }
    except requests.exceptions.RequestException as e:
        return {
            'name': service['name'],
            'url': service['url'],
            'status': f'Error: {str(e)}',
            'data': None
        }

def inject_card_container_css(html_content, service_name):
    """Inject CSS and JavaScript to ensure proper containment within card."""
    # Only inject if it's a complete HTML document
    if not html_content.strip().startswith('<!DOCTYPE') and not html_content.strip().startswith('<html'):
        # For partial HTML content, wrap it in a complete HTML document
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{service_name} Content</title>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
    
    # Sanitize service name for use as a message identifier
    service_id = service_name.lower().replace(' ', '_')
    
    # Define base style to ensure content fits in cards
    base_style = """
    html, body {
        margin: 0;
        padding: 0;
        overflow: auto;
        height: 100%;
        width: 100%;
        font-family: Arial, sans-serif;
        box-sizing: border-box;
    }
    body {
        padding: 8px;
        box-sizing: border-box;
    }
    img, video, iframe {
        max-width: 100%;
        height: auto;
    }
    
    /* Responsive classes you can use in HTML content */
    .hide-on-small {
        /* Will be hidden when container is narrow */
    }
    .responsive-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 8px;
    }
    @media (max-width: 300px) {
        .responsive-text {
            font-size: 0.8em;
        }
    }
    """
    
    # Inject script for parent-container communication and resizing
    card_script = f"""
    // Function to handle messages from inside the card
    function handleCardAction(action, data) {{
        // Create a message for the parent window
        const message = {{
            serviceId: '{service_id}',
            action: action,
            data: data
        }};
        
        // Send message to parent window
        window.parent.postMessage(message, '*');
    }}
    
    // Listen for resize messages from parent
    window.addEventListener('message', function(event) {{
        if (event.data && event.data.type === 'card-resize') {{
            // Adjust content based on new dimensions
            applyResponsiveStyles(event.data.width, event.data.height);
        }}
        
        // Handle callbacks from parent
        if (event.data && event.data.type === 'callback') {{
            const callbackEvent = new CustomEvent('card-callback', {{
                detail: event.data
            }});
            document.dispatchEvent(callbackEvent);
        }}
    }});
    
    // Function to apply responsive styles based on container size
    function applyResponsiveStyles(width, height) {{
        // You can implement responsive behavior here
        // For example, hide elements when width is small
        if (width < 300) {{
            document.querySelectorAll('.hide-on-small').forEach(el => {{
                el.style.display = 'none';
            }});
        }} else {{
            document.querySelectorAll('.hide-on-small').forEach(el => {{
                el.style.display = '';
            }});
        }}
        
        // Trigger an event that content can listen for
        document.dispatchEvent(new CustomEvent('card-resize', {{
            detail: {{ width, height }}
        }}));
    }}
    
    // Add resize observer to track content changes
    document.addEventListener('DOMContentLoaded', function() {{
        // Initialize any responsive behavior
        setTimeout(function() {{
            // Request optimal size from parent
            handleCardAction('resize-request', {{
                contentHeight: document.body.scrollHeight
            }});
            
            // Apply initial responsive styles
            const width = window.innerWidth;
            const height = window.innerHeight;
            applyResponsiveStyles(width, height);
            
            // Signal to parent that content is ready
            handleCardAction('content-ready', {{ 
                contentHeight: document.body.scrollHeight,
                hasScripts: document.querySelectorAll('script').length > 0
            }});
        }}, 100);
    }});
    """
    
    # Check if there's a head tag to inject into
    if '</head>' in html_content:
        # Create style tag
        style_tag = f"<style>{base_style}</style>"
        script_tag = f"<script>{card_script}</script>"
        
        # Insert before closing head tag
        html_content = html_content.replace('</head>', f'{style_tag}{script_tag}</head>')
    else:
        # If no head tag exists, create one
        head_content = f"""
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{service_name} Content</title>
            <style>{base_style}</style>
            <script>{card_script}</script>
        </head>
        """
        
        # Insert after html tag if it exists
        if '<html' in html_content:
            html_pos = html_content.find('<html')
            end_html_tag = html_content.find('>', html_pos)
            if end_html_tag != -1:
                insertion_point = end_html_tag + 1
                html_content = html_content[:insertion_point] + head_content + html_content[insertion_point:]
        else:
            # If no html tag, inject at the beginning
            html_content = f"<!DOCTYPE html>\n<html>{head_content}<body>{html_content}</body></html>"
    
    # Ensure proper doctype if missing
    if '<!DOCTYPE' not in html_content and '<!doctype' not in html_content:
        html_content = '<!DOCTYPE html>\n' + html_content
    
    # Add content base target to prevent navigation breaking out of iframe
    if '<base' not in html_content:
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', '<base target="_self"></head>')
    
    return html_content

@app.route('/')
def home():
    """Homepage that displays data from connected external services."""
    config = load_config()
    service_data = []
    
    for service in config['services']:
        service_data.append(fetch_data_from_service(service))
    
    return render_template('index.html', services=service_data)

@app.route('/refresh-service-data')
def refresh_service_data():
    """API endpoint to refresh service data without reloading the page."""
    service_name = request.args.get('name')
    config = load_config()
    
    # Find the service by name
    for service in config['services']:
        if service['name'] == service_name:
            service_data = fetch_data_from_service(service)
            return jsonify(service_data)
    
    return jsonify({"error": "Service not found"}), 404

@app.route('/card-action', methods=['POST'])
def card_action():
    """Handle actions triggered from within a card."""
    try:
        data = request.json
        service_id = data.get('serviceId')
        action = data.get('action')
        action_data = data.get('data', {})
        
        # Log the action for debugging
        app.logger.info(f"Card action received: {service_id} - {action}")
        
        # Handle different types of actions
        result = {"status": "success", "message": "Action received"}
        
        # Here you can implement custom actions based on the action type
        if action == 'test-connection':
            # Example: test a connection
            result["data"] = {"connection": "successful"}
        elif action == 'run-command':
            # Example: run a command
            command = action_data.get('command')
            result["data"] = {"command": command, "executed": True}
        elif action == 'resize-request':
            # Handle resize request from content
            content_height = action_data.get('contentHeight', 0)
            result["data"] = {"height": content_height}
            # Return a callback to trigger in the iframe
            result["callback"] = {
                "action": "height-updated",
                "height": content_height
            }
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error processing card action: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page for managing external service connections."""
    config = load_config()
    
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        
        if name and url:
            # Simple validation
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
                
            # Check if service with this name already exists
            for service in config['services']:
                if service['name'] == name:
                    service['url'] = url
                    break
            else:
                config['services'].append({'name': name, 'url': url})
                
            save_config(config)
            
        return redirect(url_for('settings'))
    
    return render_template('settings.html', services=config['services'])

@app.route('/test-connection', methods=['POST'])
def test_connection():
    """Test connection to an external service."""
    url = request.json.get('url')
    
    if not url:
        return jsonify({'status': 'Error', 'message': 'URL is required'}), 400
        
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url
        
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return jsonify({
                'status': 'Success',
                'message': 'Connection successful'
            })
        else:
            return jsonify({
                'status': 'Error',
                'message': f'HTTP Error: {response.status_code}'
            })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'Error',
            'message': str(e)
        })

@app.route('/remove-service', methods=['POST'])
def remove_service():
    """Remove a service from the configuration."""
    name = request.form.get('name')
    
    if name:
        config = load_config()
        config['services'] = [s for s in config['services'] if s['name'] != name]
        save_config(config)
        
    return redirect(url_for('settings'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False) 