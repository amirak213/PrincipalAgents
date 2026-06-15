from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import uuid
from chatbot.chat import chat

app = Flask(__name__)
CORS(app)

# Store session contexts
sessions = {}

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not session_id:
            session_id = str(uuid.uuid4())
            sessions[session_id] = True
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Run the async chat function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(chat(session_id, message))
        loop.close()
        
        return jsonify({
            'response': response,
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['POST'])
def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = True
    return jsonify({'session_id': session_id})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
